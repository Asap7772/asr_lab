import os
import pandas
import math
import argparse
import copy
import librosa
import soundfile as sf

argparser = argparse.ArgumentParser()
argparser.add_argument('--data_path', type=str, default='/Users/anikaitsingh/Desktop/speech_dataset/data_anikait', help='data path')
argparser.add_argument('--output_path', type=str, default='/Users/anikaitsingh/Desktop/speech_dataset/data_anikait_16K_5min', help='output path')
argparser.add_argument('--proportion', type=float, default=0.25, help='proportion of data to keep')
argparser.add_argument('--splits', type=str, nargs='+', default=['train', 'valid', 'test'], help='splits to split')
args = argparser.parse_args()

data_path=args.data_path
output_path=args.output_path
proportion=args.proportion
splits=args.splits

assert 0 < proportion <= 1, "Proportion must be between 0 and 1"
assert os.path.exists(data_path), f"File {data_path} does not exist"
assert len(splits) > 0, "Must have at least one split"
os.makedirs(output_path, exist_ok=True)

split_csvs = {}
for split in splits:
    csv_path = os.path.join(data_path, split + '.csv')
    assert os.path.exists(csv_path), f"File {csv_path} does not exist"
    split_csvs[split] = pandas.read_csv(csv_path)

for split, split_csv in split_csvs.items():
    num_rows = math.ceil(len(split_csv) * proportion)
    return_csv = copy.deepcopy(split_csv[:num_rows])
    
    for i in range(num_rows):
        row = split_csv.iloc[i]
        row_filename = row['file']
        row_filename = row_filename.split('/')[-1]
        row_text = row['text']
        
        new_row_filename = os.path.join(output_path.split('/')[-1], row_filename)
        return_csv['file'][i] = new_row_filename
        
        old_audio_path = os.path.join(data_path, row_filename)
        new_audio_path = os.path.join(output_path, row_filename)
        
        # Convert to 16K
        old_sr = 44100
        desired_sr = 16000
        x, sr = librosa.load(old_audio_path, sr=old_sr)
        y = librosa.resample(x, sr, desired_sr)
        sf.write(new_audio_path, y, desired_sr)
        
        
    new_csv_path = os.path.join(output_path, split + '.csv')
    pandas.DataFrame(return_csv).to_csv(new_csv_path, index=False)

    print(f"Done with {split} split.")
    print(f"Saved {num_rows} rows to {new_csv_path}.")