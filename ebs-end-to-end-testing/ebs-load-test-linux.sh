# EXAMPLE Disk I/O Load Generators

### Loop through all attached volumes and run 2 fio jobs per volume
#!/bin/bash
yum -y install fio
root_device=$(df --output=source / | tail -1)
for device_path in /dev/nvme*n*; do
  if [ "$device_path" != "$root_device" ]; then
    # Random read/write I/O
    fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=$device_path &
    # Sequential read/write I/O
    fio --name=sequential-rw --ioengine=posixaio --rw=rw --bs=128k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=$device_path &

  fi
done

### Loop through all attached volumes and run 1 fio jobs per volume
#!/bin/bash
yum -y install fio
root_device=$(df --output=source / | tail -1)
for device_path in /dev/nvme*n*; do
  if [ "$device_path" != "$root_device" ]; then
    # Random read/write I/O
    fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=$device_path &
  fi
done

### The fio job to run while logged in
sudo fio --name=random-rw --ioengine=posixaio --rw=randrw --rwmixread=70 --bs=4k --numjobs=1 --size=1g --time_based --runtime=100000h --filename=/dev/nvme1n1 &