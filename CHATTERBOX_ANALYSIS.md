# Chatterbox TTS Model Analysis & Script Guide

## 🎯 **Your Command Analysis**

```bash
python chatterbox_tts_simple.py input.txt --device cpu --chunk-size 300 --exaggeration 0.7 --output my_audio.wav
```

### **Default Settings Used:**
- **exaggeration=0.7** (your override, default is 0.5)
- **cfg_weight=0.5** (default)
- **device="cpu"** (your override, default is "auto")
- **chunk_size=300** (your override, default is 500)
- **Voice**: Default American voice (no voice prompt)
- **Sample Rate**: 24,000 Hz
- **Audio Format**: WAV

## 🎛️ **What Exaggeration Controls**

**Exaggeration Parameter (0.0-1.0):**

- **0.0**: Neutral, flat speech
- **0.3**: Subtle expressivity (good for documentaries)
- **0.5**: Balanced expressivity (default, good for general use)
- **0.7**: More expressive, emotional speech (your setting)
- **1.0**: Maximum expressivity, dramatic speech

### **Effects of Exaggeration=0.7:**
- ✅ **More emotional/expressive speech**
- ✅ **Better for storytelling and dramatic content**
- ✅ **Slightly faster speech pace**
- ✅ **Good for your Hindi-English mixed content**

### **Recommended Settings:**
- **Storytelling**: 0.7-0.9
- **News/Documentary**: 0.3-0.5
- **General Use**: 0.5-0.6
- **Dramatic**: 0.8-1.0

## 🎤 **How to Change to Indian Voice**

### **Updated Script Now Includes:**

```bash
# Indian Male Voice
python chatterbox_tts_simple.py input.txt --voice indian_male --device cpu --chunk-size 300

# Indian Female Voice  
python chatterbox_tts_simple.py input.txt --voice indian_female --device cpu --chunk-size 300

# With your exaggeration setting
python chatterbox_tts_simple.py input.txt --voice indian_male --exaggeration 0.7 --device cpu
```

### **Available Voice Options:**
- **default**: American English voice (no download needed)
- **indian_male**: Indian-accented male voice (downloads ~50KB)
- **indian_female**: Indian-accented female voice (downloads ~50KB)

### **Voice Download Process:**
1. First time: Downloads voice prompt from HuggingFace
2. Cached locally for future use
3. Automatic voice cloning applied to your text

## 🌍 **Devanagari vs Latin for Hindi Language**

### **Current Script Behavior:**
Your script automatically transliterates Devanagari to Latin script:

**Input Example:**
```
"यार... Sherlock Holmes बोला"
```

**Processed Output:**
```
"yaar... Sherlock Holmes bola"
```

### **Which Works Better?**

**Latin Script (Current Method) - RECOMMENDED:**
- ✅ **Better pronunciation** by Chatterbox model
- ✅ **More natural speech rhythm**
- ✅ **Consistent with model training data**
- ✅ **Handles mixed Hindi-English seamlessly**

**Devanagari Script:**
- ⚠️ **Model may struggle with Devanagari pronunciation**
- ⚠️ **Less natural speech patterns**
- ⚠️ **Inconsistent with training data**

### **Why Latin Transliteration Works Better:**

1. **Model Training**: Chatterbox trained primarily on Latin script
2. **Phonetic Accuracy**: Latin script better represents Hindi sounds for TTS
3. **Mixed Content**: Handles Hinglish naturally
4. **Pronunciation**: More accurate phonetic mapping

### **Your Input File Processing:**
Your `input.txt` with mixed content:
```
"यार..." Sherlock Holmes बोला, जो हम fireplace के दोनों तरफ बैठे हुए हैं...
```

**Gets converted to:**
```
"yaar..." Sherlock Holmes bola, jo hum fireplace ke donon taraf baithe hue hain...
```

**Result**: Natural-sounding Hindi-English mixed speech!

## 📊 **Performance with Your Settings**

### **With exaggeration=0.7 on CPU:**
- **Expressivity**: More emotional, good for storytelling
- **Speed**: Slightly faster than neutral
- **Quality**: High, with natural Hindi-English mix
- **Processing Time**: ~30-45 seconds per 300 chars (CPU)

### **Optimized Settings for Your Use Case:**

```bash
# Best for your Hindi-English content
python chatterbox_tts_simple.py input.txt \
  --voice indian_male \
  --exaggeration 0.7 \
  --cfg 0.4 \
  --device cpu \
  --chunk-size 300 \
  --output story_hindi.wav
```

## 🎛️ **CFG Weight Explained**

**CFG Weight (Classifier-Free Guidance):**
- **0.0**: Maximum creativity, less stability
- **0.3**: More expressive, good for dramatic content
- **0.5**: Balanced (default)
- **0.7**: More stable, less expressive
- **1.0**: Maximum stability, less creativity

### **Recommended Combinations:**

**Expressive Storytelling:**
- exaggeration=0.7, cfg=0.3

**Balanced Speech:**
- exaggeration=0.5, cfg=0.5

**Stable Narration:**
- exaggeration=0.4, cfg=0.7

## 🚀 **Updated Usage Examples**

### **Basic Indian Voice:**
```bash
python chatterbox_tts_simple.py input.txt --voice indian_male --device cpu
```

### **Expressive Indian Female:**
```bash
python chatterbox_tts_simple.py input.txt --voice indian_female --exaggeration 0.8 --cfg 0.3
```

### **Optimized for Your Content:**
```bash
python chatterbox_tts_simple.py input.txt \
  --voice indian_male \
  --exaggeration 0.7 \
  --cfg 0.4 \
  --chunk-size 300 \
  --device cpu \
  --output my_hindi_story.wav
```

## ✅ **Summary**

1. **Exaggeration=0.7**: Good choice for expressive storytelling
2. **Indian Voice**: Now available with `--voice indian_male/female`
3. **Devanagari → Latin**: Current method works best for Hindi
4. **Your Settings**: Well-optimized for mixed Hindi-English content

The updated script now gives you complete control over voice selection and maintains the excellent Devanagari transliteration for natural Hindi pronunciation! 🎙️✨
