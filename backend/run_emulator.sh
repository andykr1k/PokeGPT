#!/bin/bash

# Ensure DISPLAY is set for the emulator and automation tools
if [ -z "$DISPLAY" ]; then
    if [ -S /tmp/.X11-unix/X1 ]; then
        export DISPLAY=:1
    elif [ -S /tmp/.X11-unix/X0 ]; then
        export DISPLAY=:0
    else
        export DISPLAY=:1
    fi
fi

ROM_PATH="/home/andykrik/Downloads/PokemonPlatinum.nds"
ROM_DIR=$(dirname "$ROM_PATH")

if [ "$1" == "--continue" ]; then
    echo "Starting DeSmuME with save state 1..."
    flatpak run --filesystem="$ROM_DIR" org.desmume.DeSmuME --load-slot 1 "$ROM_PATH" &
else
    echo "Starting DeSmuME fresh..."
    flatpak run --filesystem="$ROM_DIR" org.desmume.DeSmuME "$ROM_PATH" &
fi

EMU_PID=$!

echo "--------------------------------------------------------"
echo "Emulator is running with PID $EMU_PID."
echo "Press [ENTER] in this terminal when you want to stop."
echo "--------------------------------------------------------"

read -p ""

echo "Saving state..."
# Attempt to find the DeSmuME window and send Shift+F1 to save state
if command -v xdotool >/dev/null 2>&1; then
    WID=$(xdotool search --name "DeSmuME" | head -n 1)
    if [ -n "$WID" ]; then
        # Activate window and send the save state hotkey
        xdotool windowactivate --sync "$WID"
        xdotool key --window "$WID" shift+F1
        echo "State saved to slot 1."
        sleep 1
    else
        echo "Could not find DeSmuME window to save state automatically."
    fi
else
    echo "WARNING: xdotool is not installed. Auto-saving state will NOT work."
    echo "Please install it using 'sudo apt install xdotool' for this feature to work."
    echo "Waiting 3 seconds before closing in case you want to manually save (Shift+F1)..."
    sleep 3
fi

echo "Closing emulator..."
kill $EMU_PID
echo "Done."
