import streamlit as st
import librosa
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
import os

# List of possible drums based on Master Drum Key
AVAILABLE_DRUMS = [
    "Bass 1", "Bass 2", "Snare", "Tom 1", "Tom 2", "Tom 3",
    "Floor tom 1", "Floor tom 2", "Hi-hat", "Crash", "Crash 2",
    "Splash", "China", "Ride", "Ride bell"
]

# Mapping of drums to their notation symbols (from Master Drum Key)
DRUM_SYMBOLS = {
    "Bass 1": "o",
    "Bass 2": "o",
    "Snare": "o",
    "Tom 1": "o",
    "Tom 2": "o",
    "Tom 3": "o",
    "Floor tom 1": "o",
    "Floor tom 2": "o",
    "Hi-hat": "x",
    "Crash": "x",
    "Crash 2": "x",
    "Splash": "x",
    "China": "x",
    "Ride": "x",
    "Ride bell": "x"
}

# Function to detect drum hits and classify them based on user-selected drums
def detect_drum_hits(audio_data, sr, selected_drums):
    # Onset detection
    onsets = librosa.onset.onset_detect(y=audio_data, sr=sr)
    onset_times = librosa.frames_to_time(onsets, sr=sr)
    
    # Extract amplitude at onset times to classify drum types
    onset_frames = librosa.time_to_frames(onset_times, sr=sr)
    amplitudes = np.abs(audio_data[onset_frames])
    
    # If no drums are selected, return empty list
    if not selected_drums:
        return []
    
    # Classify drum hits based on amplitude, mapping to selected drums
    drum_hits = []
    # Sort amplitudes to map to drums (highest amplitude to lowest)
    amplitude_range = max(amplitudes) - min(amplitudes) if len(amplitudes) > 0 else 1
    num_drums = len(selected_drums)
    
    for i, (time, amp) in enumerate(zip(onset_times, amplitudes)):
        # Convert NumPy float to Python float
        time = float(time)
        amp = float(amp)
        
        # Normalize amplitude to [0, 1] and map to selected drums
        if amplitude_range > 0:
            normalized_amp = (amp - min(amplitudes)) / amplitude_range
        else:
            normalized_amp = 0.5  # Default to middle if no range
        
        # Map the normalized amplitude to one of the selected drums
        # Higher amplitude -> earlier drums in the list, lower amplitude -> later drums
        drum_index = min(int(normalized_amp * num_drums), num_drums - 1)
        selected_drum = selected_drums[drum_index]
        symbol = DRUM_SYMBOLS.get(selected_drum, "o")  # Default to "o" if not found
        drum_hits.append((time, selected_drum, symbol))
    
    return drum_hits

# Function to create notation based on Master Drum Key style
def create_notation(drum_hits, duration, bpm, selected_drums):
    # Assuming 4/4 time signature, calculate beats
    beat_duration = 60 / bpm  # Duration of one beat in seconds
    
    # Initialize notation only for selected drums
    notation = {drum: [] for drum in selected_drums}
    
    # Initialize notation lines for each instrument
    grid_resolution = 16  # 16th note resolution
    total_beats = int(duration / beat_duration)
    total_slots = total_beats * grid_resolution
    
    for drum in notation:
        notation[drum] = ["-"] * total_slots
    
    # Map drum hits to the grid
    for time, drum_type, symbol in drum_hits:
        beat_position = time / beat_duration
        slot = int(beat_position * grid_resolution)
        if slot < total_slots:
            notation[drum_type][slot] = symbol
    
    # Format the notation in the style of the Master Drum Key
    notation_str = f"Drum Notation (4/4, 16th note resolution, BPM: {bpm}):\n\n"
    for drum, line in notation.items():
        # Only include drums that have hits
        if any(symbol != "-" for symbol in line):
            notation_str += f"{drum:<12} | "
            for i in range(0, total_slots, grid_resolution // 4):  # Group by quarter notes
                measure = line[i:i + grid_resolution // 4]
                notation_str += "".join(measure) + " "
            notation_str += "\n"
    
    return notation_str, drum_hits

def main():
    st.title("Drum Audio Notation Generator")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a drum audio file (WAV format)", type=['wav'])
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        with open("temp_audio.wav", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Load and process audio
        try:
            # Load audio file
            audio_data, sr = librosa.load("temp_audio.wav")
            duration = librosa.get_duration(y=audio_data, sr=sr)
            
            # Display audio player
            st.audio("temp_audio.wav", format='audio/wav')
            
            # Estimate BPM (optional, for better notation)
            estimated_bpm, _ = librosa.beat.beat_track(y=audio_data, sr=sr)
            estimated_bpm = float(estimated_bpm)
            st.write(f"Estimated BPM: {estimated_bpm:.2f}")
            
            # Allow user to set BPM
            user_bpm = st.number_input(
                "Set the BPM for the audio clip (or use estimated BPM above):",
                min_value=30.0,
                max_value=300.0,
                value=estimated_bpm,
                step=0.1
            )
            st.write(f"Using BPM: {user_bpm:.2f}")
            
            # Allow user to select drums present in the audio
            selected_drums = st.multiselect(
                "Select the drums present in the audio recording:",
                options=AVAILABLE_DRUMS,
                default=["Bass 1", "Snare", "Hi-hat"]  # Default selection
            )
            if not selected_drums:
                st.warning("Please select at least one drum to process the audio.")
            
            # Process audio
            if st.button("Process Audio") and selected_drums:
                with st.spinner("Processing audio..."):
                    # Detect drum hits based on selected drums
                    drum_hits = detect_drum_hits(audio_data, sr, selected_drums)
                    
                    # Create notation with user-specified BPM and drums
                    notation_str, hits = create_notation(drum_hits, duration, bpm=user_bpm, selected_drums=selected_drums)
                    
                    # Display results
                    st.subheader("Detected Drum Pattern")
                    st.text(notation_str)
                    
                    # Display waveform
                    fig, ax = plt.subplots()
                    librosa.display.waveshow(audio_data, sr=sr, ax=ax)
                    for time, _, _ in hits:
                        ax.axvline(x=time, color='r', linestyle='--', alpha=0.5)
                    st.pyplot(fig)
                    
                    # Save option
                    st.download_button(
                        label="Download Notation",
                        data=notation_str,
                        file_name="drum_notation.txt",
                        mime="text/plain"
                    )
                    
        except Exception as e:
            st.error(f"Error processing audio: {str(e)}")
        
        # Clean up
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")

if __name__ == "__main__":
    main()
