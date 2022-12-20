# My ASR Lab
This is a repository for my ASR lab. It contains the following files:
- `README.md`: This file.
- `collect_speech.py`: A script to collect speech data.
- `split_data.py`: A script to split the collected data into subsets.
- `Your_ASR.ipynb`: A notebook for your ASR system.
- `requirements.txt`: A file containing the required packages.

## Collecting Speech Data
To collect speech data, run the following command:
```
python collect_speech.py --which_split train --output_folder data --output_name my_data
```

## Splitting Data
To split the collected data into subsets, run the following command:
```
python split_data.py --data_path data --output_path data_split --proportion 0.5 --splits train valid test
```