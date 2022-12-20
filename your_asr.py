# -*- coding: utf-8 -*-
"""ASR Notebook -- Anikait Singh

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1iURDiEr74AgmMz4X4JIVqG3syVR_cHIk

**Task:**

😊-------------------------------------------------------

In this lab, you are going to make your speech recognizer. Specifically, given a pretrained wav2vec2 model, you should perform fine-tuning (FT) on your own speech data (English). You are required to collect **20 minutes** of your own voice that is recorded in either clean or noisy background. The content can be in any domains. Please just follow Gopala's voice format that will be given in the next few sections to deal with your voice data. Generally speaking, the duration of each utterance is suggested to be about **2s-5s**. But you can do any numbers. If it is 4s for each utterance, 20 minutes would correspond to about 300 utterances. Once you have 20 minutes data, you should perform 3 sets of experiments independently:

1. FT on the entire data (20minutes)
2. FT on 10 minutes data that is randomly sampled.
3. FT on 5 minutes data that is randomly sampled. 

For each experiment, please make sure to have train/dev/test split where the suggested ratio is 0.8 : 0.1 : 0.1. Please report WER for both dev and test set. That saying, you need **6 results in total**.

Submission:
Just **a doc or pdf file** that contains: 

(1) Colab links for all experiments. For example, if you do three experiments in three different colabs, just copy and paste all three links. If you just use one colab, then submit one. 

(2) Brief introduction of your collected corpus (where and how they were recorded, content domains, number of utterances, etc) and **your own data**! If you follow this code template and also use gdrive, please just copy and paste the gdrive link in the doc. 

(3) Brief analysis of the results.

😊-------------------------------------------------------

This code template is adapted from HugginFace [wav2vec2 code base](https://huggingface.co/docs/transformers/model_doc/wav2vec2).

Belowing is an example of performing fine-tuning on Gopala's voice with wav2vec2. You can follow this template and just replace the data with your own voice by following the same data format. So let's get started!

First, check GPU availablity. You are suggested to upgrade Colab Pro to have access to high-performance GPU. But it is not required.
"""

gpu_info = !nvidia-smi
gpu_info = '\n'.join(gpu_info)
if gpu_info.find('failed') >= 0:
  print('Not connected to a GPU')
else:
  print(gpu_info)

"""Install both `datasets` and `transformers` from master. Also, we need the `librosa` package to load audio files and the `jiwer` to evaluate our fine-tuned model using the [word error rate (WER)](https://huggingface.co/metrics/wer) metric ${}^1$."""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !pip install datasets==1.18.3
# !pip install transformers==4.17.0
# !pip install jiwer

from datasets import load_dataset, load_metric

"""Below we have already prepared Gopala's voice that is saved in gdrive. Just download it unzip it. """

#download gopala's voice
!pip install -U --no-cache-dir gdown --pre
!gdown https://drive.google.com/uc?id=1C8d1mFpwoISnrKYFuI1nEdd7xK3nwYJX
!unzip data_gopala.zip

"""**Have a look at data_gopala folder!!** Your speech data is also suggested to follow the same format. Specifically, all you need is just a folder that contains wav files as well as csv files for train/dev/test respectively.

After replacing Gopala's voice with yours, no addtional efforts are needed afterwards. Just finish the fine-tuning experiments.
"""

import os
which_data='anikait_10min'

if 'anikait' in which_data and not os.path.exists('/content/asr_lab'):
  os.system('git clone https://github.com/Asap7772/asr_lab.git')
  os.system('ln -s asr_lab/data_anikait_16K .')
  os.system('ln -s asr_lab/data_anikait_16K_5min .')
  os.system('ln -s asr_lab/data_anikait_16K_10min .')

# note my data is sampled at 44100 instead of 16000 (changed below to accomodate)
if which_data == 'anikait':
  path = 'data_anikait_16K'
elif which_data == 'anikait_5min':
  path = 'data_anikait_16K_5min'
elif which_data == 'anikait_10min':
  path = 'data_anikait_16K_10min'
elif which_data == 'gopala':
  path = 'data_gopala'
else:
  assert False, f"using invalid dataset {which_data}"

data = load_dataset(path)

data

"""Make sure your have train/dev/test split.

Let's write a short function to display some random samples of the dataset and run it a couple of times to get a feeling for the transcriptions.
"""

from datasets import ClassLabel
import random
import pandas as pd
from IPython.display import display, HTML

def show_random_elements(dataset, num_examples=10):
    assert num_examples <= len(dataset), "Can't pick more elements than there are in the dataset."
    picks = []
    for _ in range(num_examples):
        pick = random.randint(0, len(dataset)-1)
        while pick in picks:
            pick = random.randint(0, len(dataset)-1)
        picks.append(pick)
    
    df = pd.DataFrame(dataset[picks])
    display(HTML(df.to_html()))

show_random_elements(data["train"].remove_columns(["file"]), num_examples=10)

"""We can see that the transcriptions contain some special characters, such as `,.?!;:`. Without a language model, it is much harder to classify speech chunks to such special characters because they don't really correspond to a characteristic sound unit. *E.g.*, the letter `"s"` has a more or less clear sound, whereas the special character `"."` does not.
Also in order to understand the meaning of a speech signal, it is usually not necessary to include special characters in the transcription.

In addition, we normalize the text to only have lower case letters and append a word separator token at the end.
"""

import re
chars_to_ignore_regex = '[\,\?\.\!\-\;\:\"]'

def remove_special_characters(batch):
    batch["text"] = re.sub(chars_to_ignore_regex, '', batch["text"]).lower() + " "
    return batch

data = data.map(remove_special_characters)

show_random_elements(data["train"].remove_columns(["file"]))

"""Good! This looks better. We have removed most special characters from transcriptions and normalized them to lower-case only.

In CTC, it is common to classify speech chunks into letters, so we will do the same here. 
Let's extract all distinct letters of the training and test data and build our vocabulary from this set of letters.

We write a mapping function that concatenates all transcriptions into one long transcription and then transforms the string into a set of chars. 
It is important to pass the argument `batched=True` to the `map(...)` function so that the mapping function has access to all transcriptions at once.
"""

def extract_all_chars(batch):
  all_text = " ".join(batch["text"])
  vocab = list(set(all_text))
  return {"vocab": [vocab], "all_text": [all_text]}

vocabs = data.map(extract_all_chars, batched=True, batch_size=-1, keep_in_memory=True, remove_columns=data.column_names["train"])

"""Now, we create the union of all distinct letters in the training dataset and test dataset and convert the resulting list into an enumerated dictionary."""

vocab_list = list(set(vocabs["train"]["vocab"][0]))

vocab_dict = {v: k for k, v in enumerate(vocab_list)}
vocab_dict

"""Cool, we see that all letters of the alphabet occur in the dataset (which is not really surprising) and we also extracted the special characters `" "` and `'`. Note that we did not exclude those special characters because: 

- The model has to learn to predict when a word finished or else the model prediction would always be a sequence of chars which would make it impossible to separate words from each other.
- In English, we need to keep the `'` character to differentiate between words, *e.g.*, `"it's"` and `"its"` which have very different meanings.

To make it clearer that `" "` has its own token class, we give it a more visible character `|`. In addition, we also add an "unknown" token so that the model can later deal with characters not encountered in training set. 

Finally, we also add a padding token that corresponds to CTC's "*blank token*". The "blank token" is a core component of the CTC algorithm. For more information, please take a look at the "Alignment" section [here](https://distill.pub/2017/ctc/).
"""

vocab_dict["|"] = vocab_dict[" "]
del vocab_dict[" "]

vocab_dict["[UNK]"] = len(vocab_dict)
vocab_dict["[PAD]"] = len(vocab_dict)
len(vocab_dict)

"""Cool, now our vocabulary is complete and consists of 30 tokens, which means that the linear layer that we will add on top of the pretrained Wav2Vec2 checkpoint will have an output dimension of 30.

Let's now save the vocabulary as a json file.
"""

import json
with open('vocab.json', 'w') as vocab_file:
    json.dump(vocab_dict, vocab_file)

"""In a final step, we use the json file to instantiate an object of the `Wav2Vec2CTCTokenizer` class.

### Create Wav2Vec2CTCTokenizer

The [pretrained Wav2Vec2 checkpoint]( ) maps the speech signal to a sequence of context representations as illustrated in the figure above. A fine-tuned Wav2Vec2 checkpoint needs to map this sequence of context representations to its corresponding transcription so that a linear layer has to be added on top of the transformer block (shown in yellow). This linear layer is used to classifies each context representation to a token class analogous how, *e.g.*, after pretraining a linear layer is added on top of BERT's embeddings for further classification - *cf.* with *"BERT"* section of this [blog post](https://huggingface.co/blog/warm-starting-encoder-decoder).

The output size of this layer corresponds to the number of tokens in the vocabulary, which does **not** depend on Wav2Vec2's pretraining task, but only on the labeled dataset used for fine-tuning.
"""

from transformers import Wav2Vec2CTCTokenizer

tokenizer = Wav2Vec2CTCTokenizer("./vocab.json", unk_token="[UNK]", pad_token="[PAD]", word_delimiter_token="|")

"""# Training_args

This training_args does not mean we are going to train the model. We have to move this part here to avoid crash issues. If you are going tune the hyper-parameters to get better WER, just modify the arguments here.
"""

repo_name = 'wav2vec2-gopala'
from transformers import TrainingArguments

training_args = TrainingArguments(
  output_dir=repo_name,
  group_by_length=True,
  per_device_train_batch_size=2,
  evaluation_strategy="steps",
  num_train_epochs=30,
  fp16=True,
  gradient_checkpointing=True,
  save_steps=500,
  eval_steps=500,
  logging_steps=500,
  learning_rate=1e-4,
  weight_decay=0.005,
  warmup_steps=1000,
  save_total_limit=2,
)

"""### Create Wav2Vec2 Feature Extractor

A Wav2Vec2 feature extractor object requires the following parameters to be instantiated:

- `feature_size`: Speech models take a sequence of feature vectors as an input. While the length of this sequence obviously varies, the feature size should not. In the case of Wav2Vec2, the feature size is 1 because the model was trained on the raw speech signal ${}^2$.
- `sampling_rate`: The sampling rate at which the model is trained on.
- `padding_value`: For batched inference, shorter inputs need to be padded with a specific value
- `do_normalize`: Whether the input should be *zero-mean-unit-variance* normalized or not. Usually, speech models perform better when normalizing the input
- `return_attention_mask`: Whether the model should make use of an `attention_mask` for batched inference. In general, models should **always** make use of the `attention_mask` to mask padded tokens. However, due to a very specific design choice of `Wav2Vec2`'s "base" checkpoint, better results are achieved when using no `attention_mask`. This is **not** recommended for other speech models. For more information, one can take a look at [this](https://github.com/pytorch/fairseq/issues/3227) issue. **Important** If you want to use this notebook to fine-tune [large-lv60](https://huggingface.co/facebook/wav2vec2-large-lv60), this parameter should be set to `True`.
"""

from transformers import Wav2Vec2FeatureExtractor

feature_extractor = Wav2Vec2FeatureExtractor(feature_size=1, sampling_rate=16000, padding_value=0.0, do_normalize=True, return_attention_mask=False)

"""Great, Wav2Vec2's feature extraction pipeline is thereby fully defined!

To make the usage of Wav2Vec2 as user-friendly as possible, the feature extractor and tokenizer are *wrapped* into a single `Wav2Vec2Processor` class so that one only needs a `model` and `processor` object.
"""

from transformers import Wav2Vec2Processor

processor = Wav2Vec2Processor(feature_extractor=feature_extractor, tokenizer=tokenizer)

"""Next, we can prepare the dataset."""

data["train"][0]["file"]

"""Great, let's listen to a couple of audio files to better understand the dataset and verify that the audio was correctly loaded. 

**Note**: *You can click the following cell a couple of times to listen to different speech samples.*
"""

import IPython.display as ipd
import numpy as np
import random
import torchaudio

rand_int = random.randint(0, len(data["train"]))

print(data["train"][rand_int]["text"])
wav, _ = torchaudio.load(data['train'][rand_int]['file'])
ipd.Audio(data=np.asarray(wav), autoplay=True, rate=16000)

"""It can be heard, that the speakers change along with their speaking rate, accent, etc. Overall, the recordings sound relatively clear though, which is to be expected from a read speech corpus.

Let's do a final check that the data is correctly prepared, by printing the shape of the speech input, its transcription, and the corresponding sampling rate.

**Note**: *You can click the following cell a couple of times to verify multiple samples.*

Finally, we can process the dataset to the format expected by the model for training. We will make use of the `map(...)` function.

First, we load and resample the audio data, simply by calling `batch["audio"]`.
Second, we extract the `input_values` from the loaded audio file. In our case, the `Wav2Vec2Processor` only normalizes the data. For other speech models, however, this step can include more complex feature extraction, such as [Log-Mel feature extraction](https://en.wikipedia.org/wiki/Mel-frequency_cepstrum).
Third, we encode the transcriptions to label ids.

**Note**: This mapping function is a good example of how the `Wav2Vec2Processor` class should be used. In "normal" context, calling `processor(...)` is redirected to `Wav2Vec2FeatureExtractor`'s call method. When wrapping the processor into the `as_target_processor` context, however, the same method is redirected to `Wav2Vec2CTCTokenizer`'s call method.
For more information please check the [docs](https://huggingface.co/transformers/master/model_doc/wav2vec2.html#transformers.Wav2Vec2Processor.__call__).
"""

def prepare_dataset(batch):

    audio, _ = torchaudio.load(batch['file'])
    audio = audio.numpy().reshape(-1)
    batch["input_values"] = audio
    batch["input_length"] = len(batch["input_values"])

    with processor.as_target_processor():
        batch["labels"] = processor(batch["text"]).input_ids
    return batch

"""Let's apply the data preparation function to all examples."""

data = data.map(prepare_dataset, remove_columns=data.column_names["train"], num_proc=4)

"""**Note**: Currently `datasets` make use of [`torchaudio`](https://pytorch.org/audio/stable/index.html) and [`librosa`](https://librosa.org/doc/latest/index.html) for audio loading and resampling. If you wish to implement your own costumized data loading/sampling, feel free to just make use of the `"path"` column instead and disregard the `"audio"` column.

Long input sequences require a lot of memory. Since `Wav2Vec2` is based on `self-attention` the memory requirement scales quadratically with the input length for long input sequences (*cf.* with [this](https://www.reddit.com/r/MachineLearning/comments/genjvb/d_why_is_the_maximum_input_sequence_length_of/) reddit post). For this demo, let's filter all sequences that are longer than 4 seconds out of the training dataset.
"""

max_input_length_in_sec = 4.0
data["train"] = data["train"].filter(lambda x: x < max_input_length_in_sec * processor.feature_extractor.sampling_rate, input_columns=["input_length"])

"""Awesome, now we are ready to start training!

### Set-up Dataloader

Let's start by defining the data collator. The code for the data collator was copied from [this example](https://github.com/huggingface/transformers/blob/9a06b6b11bdfc42eea08fa91d0c737d1863c99e3/examples/research_projects/wav2vec2/run_asr.py#L81).
"""

import torch

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

@dataclass
class DataCollatorCTCWithPadding:
    """
    Data collator that will dynamically pad the inputs received.
    Args:
        processor (:class:`~transformers.Wav2Vec2Processor`)
            The processor used for proccessing the data.
        padding (:obj:`bool`, :obj:`str` or :class:`~transformers.tokenization_utils_base.PaddingStrategy`, `optional`, defaults to :obj:`True`):
            Select a strategy to pad the returned sequences (according to the model's padding side and padding index)
            among:
            * :obj:`True` or :obj:`'longest'`: Pad to the longest sequence in the batch (or no padding if only a single
              sequence if provided).
            * :obj:`'max_length'`: Pad to a maximum length specified with the argument :obj:`max_length` or to the
              maximum acceptable input length for the model if that argument is not provided.
            * :obj:`False` or :obj:`'do_not_pad'` (default): No padding (i.e., can output a batch with sequences of
              different lengths).
    """

    processor: Wav2Vec2Processor
    padding: Union[bool, str] = True

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        # split inputs and labels since they have to be of different lenghts and need
        # different padding methods
        input_features = [{"input_values": feature["input_values"]} for feature in features]
        label_features = [{"input_ids": feature["labels"]} for feature in features]

        batch = self.processor.pad(
            input_features,
            padding=self.padding,
            return_tensors="pt",
        )
        with self.processor.as_target_processor():
            labels_batch = self.processor.pad(
                label_features,
                padding=self.padding,
                return_tensors="pt",
            )

        # replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)

        batch["labels"] = labels

        return batch

data_collator = DataCollatorCTCWithPadding(processor=processor, padding=True)

"""Next, the evaluation metric is defined. As mentioned earlier, the 
predominant metric in ASR is the word error rate (WER), hence we will use it in this notebook as well.
"""

wer_metric = load_metric("wer")

"""The model will return a sequence of logit vectors:
$\mathbf{y}_1, \ldots, \mathbf{y}_m$ with $\mathbf{y}_1 = f_{\theta}(x_1, \ldots, x_n)[0]$ and $n >> m$.

A logit vector $\mathbf{y}_1$ contains the log-odds for each word in the vocabulary we defined earlier, thus $\text{len}(\mathbf{y}_i) =$ `config.vocab_size`. We are interested in the most likely prediction of the model and thus take the `argmax(...)` of the logits. Also, we transform the encoded labels back to the original string by replacing `-100` with the `pad_token_id` and decoding the ids while making sure that consecutive tokens are **not** grouped to the same token in CTC style ${}^1$.
"""

def compute_metrics(pred):
    pred_logits = pred.predictions
    pred_ids = np.argmax(pred_logits, axis=-1)

    pred.label_ids[pred.label_ids == -100] = processor.tokenizer.pad_token_id

    pred_str = processor.batch_decode(pred_ids)
    # we do not want to group tokens when computing the metrics
    label_str = processor.batch_decode(pred.label_ids, group_tokens=False)

    wer = wer_metric.compute(predictions=pred_str, references=label_str)

    return {"wer": wer}

"""Now, we can load the pretrained `Wav2Vec2` checkpoint. The tokenizer's `pad_token_id` must be to define the model's `pad_token_id` or in the case of `Wav2Vec2ForCTC` also CTC's *blank token* ${}^2$. To save GPU memory, we enable PyTorch's [gradient checkpointing](https://pytorch.org/docs/stable/checkpoint.html) and also set the loss reduction to "*mean*"."""

from transformers import Wav2Vec2ForCTC

model = Wav2Vec2ForCTC.from_pretrained(
    "facebook/wav2vec2-base",
    ctc_loss_reduction="mean", 
    pad_token_id=processor.tokenizer.pad_token_id,
)

model = model.cuda()

"""### Training

Typically, it is useful to freeze the encoder for low resource/few show settings. 
"""

model.freeze_feature_encoder()

"""Now, all instances can be passed to Trainer and we are ready to start training!"""

from transformers import Trainer


trainer = Trainer(
    model=model,
    data_collator=data_collator,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=data["train"],
    eval_dataset=data["validation"],
    tokenizer=processor.feature_extractor,
)

"""---

${}^1$ To allow models to become independent of the speaker rate, in CTC, consecutive tokens that are identical are simply grouped as a single token. However, the encoded labels should not be grouped when decoding since they don't correspond to the predicted tokens of the model, which is why the `group_tokens=False` parameter has to be passed. If we wouldn't pass this parameter a word like `"hello"` would incorrectly be encoded, and decoded as `"helo"`.

${}^2$ The blank token allows the model to predict a word, such as `"hello"` by forcing it to insert the blank token between the two l's. A CTC-conform prediction of `"hello"` of our model would be `[PAD] [PAD] "h" "e" "e" "l" "l" [PAD] "l" "o" "o" [PAD]`.

```javascript
function ConnectButton(){
    console.log("Connect pushed"); 
    document.querySelector("#top-toolbar > colab-connect-button").shadowRoot.querySelector("#connect").click() 
}
setInterval(ConnectButton,60000);
```

Depending on what GPU was allocated to your google colab it might be possible that you are seeing an `"out-of-memory"` error here. In this case, it's probably best to reduce `per_device_train_batch_size` to 16 or even less and eventually make use of [`gradient_accumulation`](https://huggingface.co/transformers/master/main_classes/trainer.html#trainingarguments).
"""

!rm -rf /content/wav2vec2-gopala
trainer.train()

"""The final dev WER here is about 0.41.

### Evaluate

In the final part, we run our model on some of the validation data to get a feeling for how well it works.

Let's load the `model`. Make sure the model path exists.!
"""

model = Wav2Vec2ForCTC.from_pretrained("wav2vec2-gopala/checkpoint-1500").cuda()

"""Now, we will make use of the `map(...)` function to predict the transcription of every test sample and to save the prediction in the dataset itself. We will call the resulting dictionary `"results"`. 

**Note**: we evaluate the test data set with `batch_size=1` on purpose due to this [issue](https://github.com/pytorch/fairseq/issues/3227). Since padded inputs don't yield the exact same output as non-padded inputs, a better WER can be achieved by not padding the input at all.
"""

def map_to_result(batch):
  with torch.no_grad():
    input_values = torch.tensor(batch["input_values"]).unsqueeze(0)
    input_values = input_values.cuda()
    logits = model(input_values).logits

  pred_ids = torch.argmax(logits, dim=-1)
  batch["pred_str"] = processor.batch_decode(pred_ids)[0]
  batch["text"] = processor.decode(batch["labels"], group_tokens=False)
  
  return batch

results = data["test"].map(map_to_result, remove_columns=data["test"].column_names)

"""Let's compute the overall test WER!"""

print("Test WER: {:.3f}".format(wer_metric.compute(predictions=results["pred_str"], references=results["text"])))

"""Let's take a look at some predictions to see what errors are made by the model."""

try:
  show_random_elements(results)
except:
  show_random_elements(results, 8)

"""It becomes clear that the predicted transcriptions are acoustically very similar to the target transcriptions, but often contain spelling or grammatical errors. This shouldn't be very surprising though given that we purely rely on Wav2Vec2 without making use of a language model.

Finally, to better understand how CTC works, it is worth taking a deeper look at the exact output of the model. Let's run the first test sample through the model, take the predicted ids and convert them to their corresponding tokens.
"""

model.to("cuda")

with torch.no_grad():
  logits = model(torch.tensor(data["test"][:1]["input_values"], device="cuda")).logits

pred_ids = torch.argmax(logits, dim=-1)

# convert ids to tokens
" ".join(processor.tokenizer.convert_ids_to_tokens(pred_ids[0].tolist()))

"""The output should make it a bit clearer how CTC works in practice. The model is to some extent invariant to speaking rate since it has learned to either just repeat the same token in case the speech chunk to be classified still corresponds to the same token. This makes CTC a very powerful algorithm for speech recognition since the speech file's transcription is often very much independent of its length."""

