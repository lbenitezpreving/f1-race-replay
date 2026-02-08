import subprocess
import sys
import time
import os

def main():
    # Configuration - Default to 2023 Season Opener (Bahrain)
    # Using a past race ensures data is likely available
    YEAR = 2023
    ROUND = 1
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_root, "main.py")
    
    print(f"--- F1 Race Replay Debug Launcher ---")
    print(f"Target Session: {YEAR} Round {ROUND}")
    print("This script will launch:")
    print("1. Race Replay (with telemetry enabled)")
    print("2. Weather Viewer")
    print("-" * 40)
    
    # 1. Launch Race Replay (Viewer + Telemetry)
    print(f"[1/2] Launching Race Replay...")
    race_cmd = [
        sys.executable, 
        main_script, 
        "--viewer", 
        "--telemetry", 
        "--year", str(YEAR), 
        "--round", str(ROUND)
    ]
    
    # Launch in a new console window if possible, or just spawn
    # passing env ensures it uses the same python environment
    race_process = subprocess.Popen(race_cmd)
    
    # 2. Wait for initialization
    # Give the race replay enough time to start the telemetry server
    print("Waiting 5 seconds for race replay to initialize...")
    time.sleep(5)
    
    # 3. Launch Weather Viewer
    print(f"[2/2] Launching Weather Viewer (Debug Rain Mode)...")
    weather_cmd = [sys.executable, "-m", "src.gui.weather_viewer", "--debug-rain"]
    weather_process = subprocess.Popen(weather_cmd)
    
    print("\nBoth processes are running.")
    print(">> Press Ctrl+C in this terminal to stop both processes <<")
    
    try:
        while True:
            time.sleep(1)
            # Check if processes are still alive
            if race_process.poll() is not None:
                print("\nRace replay process exited.")
                break
            if weather_process.poll() is not None:
                print("\nWeather viewer process exited.")
                break
    except KeyboardInterrupt:
        print("\nStopping processes...")
    finally:
        # Force kill/terminate if still running
        if race_process.poll() is None:
            print("Terminating Race Replay...")
            race_process.terminate()
        
        if weather_process.poll() is None:
            print("Terminating Weather Viewer...")
            weather_process.terminate()
            
        print("Cleanup complete.")

if __name__ == "__main__":
    main()
