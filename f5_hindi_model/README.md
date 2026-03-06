---
license: cc-by-4.0
library_name: f5-tts
datasets:
- SPRINGLab/IndicTTS-Hindi
- SPRINGLab/IndicVoices-R_Hindi
language:
- hi
pipeline_tag: text-to-speech
widget:
  - text: "उसके दोस्त, प्रेमिकाएँ, और रिश्तेदार, उसे इसी नाम से बुलाते थे, और वो भी, अक्सर समझ जाता था, कि क्वैं उसी को संबोधित है"
    output:
      url: samples/output1.wav
      
  - text: "इस बागीचे में, आप शुरू से अन्त तक घूम आइये, तो दुनिया भर की सुन्दर चीज़ों के साथ, एक अनन्यता महसूस करेंगें"
    output:
      url: samples/output2.wav
      
  - text: "शिवगढ़ी गाँव, एक बड़ा गाँव था, और उसमेँ सबसे बड़ा मकान, पण्डित दुर्गाशङ्कर श्रीमुख का था"
    output:
      url: samples/output3.wav
---

# F5-TTS Hindi 24KHz Model

This is a Hindi Text-to-Speech model trained from scratch using the [F5 architecture](https://arxiv.org/abs/2410.06885).

# Details

- **Developed by:** SPRING Lab, Indian Institute of Technology, Madras
- **Language:** Hindi
- **License:** CC-BY-4.0

## Uses

The model was developed and is primarily intended for research purposes.

## How to Get Started with the Model

Clone the following github repo and refer to the README: https://github.com/rumourscape/F5-TTS

## Training Details

The model was trained on 8x A100 40GB GPUs for close to a week. We would like to thank [CDAC](https://cdac.in/) for providing the compute resources.

We used the "small" configuration(151M parameter) model for training according to the F5 paper.

### Training Data

We used the Hindi subsets of [IndicTTS](https://www.tsdconference.org/tsd2016/download/cbblr16-850.pdf) and [IndicVoices-R](https://arxiv.org/pdf/2409.05356) datasets for training this model.
<br>
- **IndicTTS-Hindi:** https://huggingface.co/datasets/SPRINGLab/IndicTTS-Hindi
<br>
- **IndicVoices-R_Hindi:** https://huggingface.co/datasets/SPRINGLab/IndicVoices-R_Hindi
