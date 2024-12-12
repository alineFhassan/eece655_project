#!/bin/bash

echo "Enabling IPv4 IP forwarding..."
sudo sysctl -w net.ipv4.ip_forward=1
# i hardcoded them just for saving time. they can be extracted from packet
ATTACKER_IP="192.168.11.201"  
HONEYPOT_IP="192.168.11.160"
SNORT_IP="192.168.11.154"

echo "Enter sudo password to run Snort: "
read -s sudo_password

command="sudo snort -v -q -l /var/log/snort -i enp0s3 -A console -c /etc/snort/snort.conf"
echo "$sudo_password" | sudo -S $command 2>&1 | tee ./logfile.txt | while read -r line
do
    if [[ "$line" == *"Possible SIP Flood Attack"* ]]; then
        echo "Parsing log: $line"

        src=$(echo "$line" | grep -oP '(?<=\{UDP\} )\d{1,3}(\.\d{1,3}){3}:\d+')
        dst=$(echo "$line" | grep -oP '(?<=-> )\d{1,3}(\.\d{1,3}){3}:\d+')


        src_ip=$(echo "$src" | cut -d':' -f1)
        src_port=$(echo "$src" | cut -d':' -f2)
        dst_ip=$(echo "$dst" | cut -d':' -f1)
        dst_port=$(echo "$dst" | cut -d':' -f2)

        if [[ -z "$src_ip" || -z "$src_port" || -z "$dst_ip" || -z "$dst_port" ]]; then
            echo "Invalid log format or missing data. Skipping entry."
            continue
        fi

        echo "Detected SIP Flood attack: $src_ip:$src_port -> $dst_ip:$dst_port"
        echo "Setting up iptables rules for IPv4 packet forwarding..."

        sudo iptables -F
        sudo iptables -t nat -F
        sudo iptables -X

        echo "Current iptables NAT rules (IPv4):"
        sudo iptables -t nat -L -v

        echo "Current iptables FORWARD rules (IPv4):"
        sudo iptables -L -v

        echo "Adding PREROUTING rule for IPv4 source $ATTACKER_IP:$src_port -> $HONEYPOT_IP:5060"
        sudo iptables -t nat -A PREROUTING -p udp --dport 5060 -j DNAT --to-destination "$HONEYPOT_IP"


        echo "Adding FORWARD rule for IPv4 packets from $ATTACKER_IP to $HONEYPOT_IP:5060"
        sudo iptables -A FORWARD -p udp -d "$HONEYPOT_IP" --dport 5060 -j ACCEPT
        echo "Adding FORWARD rule for IPv4 packets from $HONEYPOT_IP:5060 back to $ATTACKER_IP"
        sudo iptables -A INPUT -p udp --dport 5060 -j ACCEPT
        sudo iptables -A OUTPUT -p udp --sport 5060 -j ACCEPT

 
        echo "Current iptables NAT rules (IPv4):"
        sudo iptables -t nat -L -v

        echo "Current iptables FORWARD rules (IPv4):"
        sudo iptables -L -v
    fi
done

