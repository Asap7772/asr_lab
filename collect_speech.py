import os
import pyaudio
import wave
import pandas
import copy
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--which_split', type=str, default='test', help='train, valid, test')
parser.add_argument('--output_folder', type=str, default='/Users/anikaitsingh/Desktop/speech_dataset/', help='output folder')
parser.add_argument('--output_name', type=str, default='data_anikait', help='output name')
parser.add_argument('--hotstart', type=int, default=0, help='skip to this index')
args = parser.parse_args()

which_split=args.which_split
output_folder=args.output_folder
file_to_gopala=os.path.join(output_folder, 'data_gopala')
output_name=args.output_name
output_path = os.path.join(output_folder, output_name)

os.makedirs(output_path, exist_ok=True)

csv_path = os.path.join(file_to_gopala, which_split + '.csv')
assert os.path.exists(csv_path), f"File {csv_path} does not exist"
split_csv = pandas.read_csv(csv_path)

def record_audio(filename = "recorded.wav", text_to_record='', chunk = 1024, FORMAT = pyaudio.paInt16, channels=1, sample_rate = 44100, record_seconds = 5):
    p = pyaudio.PyAudio()
    # open stream object as input & output
    stream = p.open(format=FORMAT,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    output=True,
                    frames_per_buffer=chunk)
    frames = []
    print("Recording...")
    print("Say: " + text_to_record)
    for i in range(int(sample_rate / chunk * record_seconds)):
        data = stream.read(chunk)
        # if you want to hear your voice while recording
        # stream.write(data)
        frames.append(data)
    print("Finished recording.")
    # stop and close stream
    stream.stop_stream()
    stream.close()
    # terminate pyaudio object
    p.terminate()
    # save audio file
    # open the file in 'write bytes' mode
    wf = wave.open(filename, "wb")
    # set the channels
    wf.setnchannels(channels)
    # set the sample format
    wf.setsampwidth(p.get_sample_size(FORMAT))
    # set the sample rate
    wf.setframerate(sample_rate)
    # write the frames as bytes
    wf.writeframes(b"".join(frames))
    # close the file
    wf.close()
    
print(split_csv.head())

output_slip_csv = copy.deepcopy(split_csv)

k = 0
while k < len(split_csv):
    row = split_csv.iloc[k]
    row_filename = row['file']
    row_text = row['text']
    
    new_filename = row_filename.split('/')[1]
    new_filename = os.path.join(output_name, new_filename)
    output_slip_csv['file'][k] = new_filename
    
    if k < args.hotstart:
        k += 1
        continue
    elif k == args.hotstart:
        print("Hotstart at index: " + str(k))
        
    record_audio(filename = os.path.join(output_folder, new_filename), text_to_record=row_text, record_seconds=4)
    recording_out = input(f"Index {k}, Press x to stop, r to rerecord, any other key to continue: ")
    
    if recording_out != 'r':
        k += 1
        
    if recording_out == 'x':
        break

output_slip_csv = output_slip_csv[:k]
pandas.DataFrame(output_slip_csv).to_csv(os.path.join(output_path, which_split + '.csv'), index=False)

print("Done")