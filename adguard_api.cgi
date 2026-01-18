#!/bin/sh
echo "Content-type: application/json"
echo ""

# Read Query String
read POST_DATA

# Function to get current schedules
get_schedules() {
    echo "["
    first=1
    crontab -l | grep "adguardhome" | while read -r line; do
        if [ "$first" -eq 0 ]; then echo ","; fi
        
        # Parse cron line: m h * * * command
        min=$(echo "$line" | awk '{print $1}')
        hour=$(echo "$line" | awk '{print $2}')
        
        # Check action based on the payload (true/false)
        if echo "$line" | grep -q "enabled\": true"; then
            action="ON"
        else
            action="OFF"
        fi
        
        # Create a simple ID hash from the line
        id=$(echo "$line" | md5sum | awk '{print $1}')
        
        echo "{\"id\": \"$id\", \"hour\": \"$hour\", \"min\": \"$min\", \"action\": \"$action\"}"
        first=0
    done
    echo "]"
}

# Function to add schedule
add_schedule() {
    # Extract params (very basic parsing for simplicity in shell)
    # Expected format from fetch: hour=HH&min=MM&action=ON/OFF
    
    # We will accept arguments passed to the script for simplicity or parse simple query string
    hour=$(echo "$QUERY_STRING" | grep -o 'hour=[0-9]*' | cut -d= -f2)
    min=$(echo "$QUERY_STRING" | grep -o 'min=[0-9]*' | cut -d= -f2)
    action=$(echo "$QUERY_STRING" | grep -o 'action=[A-Z]*' | cut -d= -f2)

    if [ -z "$hour" ] || [ -z "$min" ] || [ -z "$action" ]; then
        echo "{\"status\": "error", \"message\": \"Missing parameters\"}"
        return
    fi
    
    bool_val="false"
    if [ "$action" = "ON" ]; then
        bool_val="true"
    fi
    
    # The Command
    cmd="curl -X POST -H \"Content-Type: application/json\" -d '{\"enabled\": $bool_val}' http://127.0.0.1:3000/control/filtering/config >/dev/null 2>&1"
    
    # Cron Entry
    cron_line="$min $hour * * * $cmd # adguardhome"
    
    # Append to crontab
    (crontab -l 2>/dev/null; echo "$cron_line") | crontab -
    
    echo "{\"status\": \"success\"}"
}

# Function to delete schedule
delete_schedule() {
    del_id=$(echo "$QUERY_STRING" | grep -o 'id=[a-z0-9]*' | cut -d= -f2)
    
    # We need to rebuild crontab excluding the matching line
    # This is tricky in shell without a temp file, so we use one
    tmp="/tmp/cron.tmp"
    crontab -l > "$tmp"
    
    # Loop and calculate hash to find match
    mv "$tmp" "$tmp.old"
    touch "$tmp"
    
    while read -r line; do
        # Calculate hash of this line
        line_id=$(echo "$line" | md5sum | awk '{print $1}')
        
        # If ID matches and it is an adguard line, skip it
        if [ "$line_id" = "$del_id" ] && echo "$line" | grep -q "adguardhome"; then
            continue
        fi
        echo "$line" >> "$tmp"
    done < "$tmp.old"
    
    crontab "$tmp"
    rm "$tmp" "$tmp.old"
    
    echo "{\"status\": \"success\"}"
}

# Router Logic
mode=$(echo "$QUERY_STRING" | grep -o 'mode=[a-z]*' | cut -d= -f2)

case "$mode" in
    add)
        add_schedule
        ;;
    del)
        delete_schedule
        ;;
    list)
        get_schedules
        ;;
    *)
        echo "{\"error\": \"Unknown mode\"}"
        ;;
esac
