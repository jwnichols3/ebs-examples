from datetime import datetime
import time
import subprocess
import argparse


def run_command(command):
    """Run a shell command."""
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    return stdout.decode("utf-8"), stderr.decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="End-to-end test script.")
    parser.add_argument(
        "--wait-time",
        type=int,
        default=120,
        help="Time to wait before cleaning up resources (in seconds).",
    )
    args = parser.parse_args()

    # Start datetime stamp
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"Starting the script at {start_datetime}")

    # Step 1: Create EC2 instances and EBS volumes with "App" tag using ebs-ec2-launch-loadtest.py
    print("Creating EC2 instances and EBS volumes...")
    stdout, stderr = run_command(
        f"python ebs-ec2-launch-loadtest.py --tag App={start_datetime}"
    )
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")
        return

    # Step 2: Test --create option in ebs-cw-alarm-impairedvol.py
    print("Testing --create option...")
    stdout, stderr = run_command("python ebs-cw-alarm-impairedvol.py --create")
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")
        return

    # Step 3: Wait for the specified time
    print(f"Waiting for {args.wait_time} seconds...")
    time.sleep(args.wait_time)

    # Step 4: Test --update option
    update_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Updating the 'App' tag to {update_datetime}...")
    stdout, stderr = run_command(
        f"python ebs-ec2-launch-loadtest.py --update-tag App={update_datetime}"
    )
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")
        return

    # Step 5: Test --cleanup option
    print("Testing --cleanup option...")
    stdout, stderr = run_command("python ebs-cw-alarm-impairedvol.py --cleanup")
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")
        return

    # Step 6: Terminate EC2 instances
    print("Terminating EC2 instances...")
    stdout, stderr = run_command("python ebs-ec2-launch-loadtest.py --terminate")
    print(stdout)
    if stderr:
        print(f"Error: {stderr}")
        return

    print("End-to-end testing completed.")


if __name__ == "__main__":
    print("\n\n\IN DEVELOPMENT\n\n\n")
    main()
