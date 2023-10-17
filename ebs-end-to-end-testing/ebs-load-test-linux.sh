# EXAMPLE Disk I/O Load Generators

### Loop through all attached volumes and run 2 fio jobs per volume
#!/bin/bash
yum -y install fio
root_device=$(df --output=source / | tail -1)
for device_path in /dev/nvme*n*; do
  if [ "$device_path" != "$root_device" ]; then
    # Random read/write I/O
    fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=256m --time_based --runtime=100000h --filename=$device_path &
    # Sequential read/write I/O
    fio --name=sequential-rw --ioengine=posixaio --rw=rw --bs=128k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=$device_path &

  fi
done

### Loop through all attached volumes and run 1 fio jobs per volume

#!/bin/bash
yum -y install fio

# Get the root partition and the root device
root_partition=$(df --output=source / | tail -1)
root_device=$(echo $root_partition | sed -E 's/p[0-9]+$//')

for device_path in /dev/nvme*n1; do  # Only match NVMe namespaces, not partitions
  # Skip if the device_path is the root device or the root partition
  if [[ "$device_path" != "$root_device" && "$device_path" != "$root_partition" ]]; then
    device_name=$(basename $device_path)
    # Random read/write I/O
    fio --name=random-rw_${device_name} --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=2m --time_based --runtime=100000h --filename=$device_path &
  fi
done

## Partition and format the additional EBS volumes and run random and sequencial:

#!/bin/bash
yum -y install fio
yum -y install parted

# Get the root partition and the root device
root_partition=$(df --output=source / | tail -1)
root_device=$(echo $root_partition | sed -E 's/p[0-9]+$//')

for device_path in /dev/nvme*n1; do  # Only match NVMe namespaces, not partitions
  # Skip if the device_path is the root device or the root partition
  if [[ "$device_path" != "$root_device" && "$device_path" != "$root_partition" ]]; then
    device_name=$(basename $device_path)
    
    # Create a single partition on the device
    parted $device_path --script mklabel gpt mkpart primary ext4 0% 100%
    
    # Wait a bit for the partition table to get re-read
    sleep 5
    
    # Format the partition to ext4
    mkfs.ext4 "${device_path}p1"
    
    # Create a mount point and mount the partition
    mkdir -p "/mnt/${device_name}"
    mount "${device_path}p1" "/mnt/${device_name}"
    
    # Random read/write I/O
    fio --name=random-rw_${device_name} --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=2m --time_based --runtime=100000h --filename="/mnt/${device_name}/fio_test_file" &

    fio --name=sequential-rw_${device_name} --ioengine=posixaio --rw=rw --bs=128k --numjobs=1 --size=1g --time_based --runtime=100000h --filename="/mnt/${device_name}/fio_test_file" &
  fi
done


### The fio job to run while logged in
sudo fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=/dev/nvme1n1 &