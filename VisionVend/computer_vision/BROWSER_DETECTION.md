# Browser Object Detection

Transformers.js

### State-of-the-art Machine Learning for the Web

Run 🤗 Transformers directly in your browser, with no need for a server!

Transformers.js is designed to be functionally equivalent to Hugging Face’s [transformers](https://github.com/huggingface/transformers) python library, meaning you can run the same pretrained models using a very similar API. These models support common tasks in different modalities, such as:

* 📝  **Natural Language Processing** : text classification, named entity recognition, question answering, language modeling, summarization, translation, multiple choice, and text generation.
* 🖼️  **Computer Vision** : image classification, object detection, segmentation, and depth estimation.
* 🗣️  **Audio** : automatic speech recognition, audio classification, and text-to-speech.
* 🐙  **Multimodal** : embeddings, zero-shot audio classification, zero-shot image classification, and zero-shot object detection.

Transformers.js uses [ONNX Runtime](https://onnxruntime.ai/) to run models in the browser. The best part about it, is that you can easily [convert](https://huggingface.co/docs/transformers.js/index#convert-your-models-to-onnx) your pretrained PyTorch, TensorFlow, or JAX models to ONNX using [🤗 Optimum](https://github.com/huggingface/optimum#onnx--onnx-runtime).

For more information, check out the full [documentation](https://huggingface.co/docs/transformers.js).

## Quick tour

It’s super simple to translate from existing code! Just like the python library, we support the `pipeline` API. Pipelines group together a pretrained model with preprocessing of inputs and postprocessing of outputs, making it the easiest way to run models with the library.

| **Python (original)** | **Javascript (ours)** |
| :-------------------------: | :-------------------------: |
|           Copied           |                            |

```
from transformers import pipeline

# Allocate a pipeline for sentiment-analysis
pipe = pipeline('sentiment-analysis')

out = pipe('I love transformers!')
# [{'label': 'POSITIVE', 'score': 0.999806941}]
```

 | Copied

```
import { pipeline } from '@huggingface/transformers';

// Allocate a pipeline for sentiment-analysis
const pipe = await pipeline('sentiment-analysis');

const out = await pipe('I love transformers!');
// [{'label': 'POSITIVE', 'score': 0.999817686}]
```

 |

You can also use a different model by specifying the model id or path as the second argument to the `pipeline` function. For example:

Copied

```
// Use a different model for sentiment-analysis
const pipe = await pipeline('sentiment-analysis', 'Xenova/bert-base-multilingual-uncased-sentiment');
```

By default, when running in the browser, the model will be run on your CPU (via WASM). If you would like to run the model on your GPU (via WebGPU), you can do this by setting `device: 'webgpu'`, for example:

Copied

```
// Run the model on WebGPU
const pipe = await pipeline('sentiment-analysis', 'Xenova/distilbert-base-uncased-finetuned-sst-2-english', {
  device: 'webgpu',
});
```

For more information, check out the [WebGPU guide](https://huggingface.co/docs/transformers.js/guides/webgpu).

The WebGPU API is still experimental in many browsers, so if you run into any issues, please file a [bug report](https://github.com/huggingface/transformers.js/issues/new?title=%5BWebGPU%5D%20Error%20running%20MODEL_ID_GOES_HERE&assignees=&labels=bug,webgpu&projects=&template=1_bug-report.yml).

In resource-constrained environments, such as web browsers, it is advisable to use a quantized version of the model to lower bandwidth and optimize performance. This can be achieved by adjusting the `dtype` option, which allows you to select the appropriate data type for your model. While the available options may vary depending on the specific model, typical choices include `"fp32"` (default for WebGPU), `"fp16"`, `"q8"` (default for WASM), and `"q4"`. For more information, check out the [quantization guide](https://huggingface.co/docs/transformers.js/guides/dtypes).

Copied

```
// Run the model at 4-bit quantization
const pipe = await pipeline('sentiment-analysis', 'Xenova/distilbert-base-uncased-finetuned-sst-2-english', {
  dtype: 'q4',
});
```
