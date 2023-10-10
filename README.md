# AI Companion llama.cpp server

Made for https://github.com/skycover/aicom-obsidian/ project.

This is the simple one-evening built server that run llama.cpp
via the python bingings.

In fact, both llama.cpp and llama-cpp-python already have a good servers inside themselves.
The main goal to make another one is to set up a minimalistic sandbox to experiment for
various unusual things via simple python code without any infrastructure complications.

The interact_llamacpp.py from https://github.com/IlyaGusev/rulm was got as the bones.

## API

```
POST: /query
{
    key: string,
    params: {'top_p', 'top_k', 'temperature', 'repeat_penalty'},
    messages: [[role, content]...]
}
return 200, int: total number of tokens.
```

Call /query it to start inference.

'key' is optional, checked if --key was given.

'params' may be {}. In this case the server defaults are used.

Role is one of: system, user, bot.

```
GET: /receive?key=string
return 200, str: one token OR '' if no tokens ready OR '[[END OF AICOM SENTENCE]]' if inference completed.
```

'key' is optional, checked if --key was given.

You should check /receive repeatedly, ignoring empty results until '[[END OF AICOM SENTENCE]]' will be received.

If you'll stop check, then the inference will stop till the next request. Simple stop requests if you
don't want to get the rest of inference.

If you'll send a new /query, then inference will be restarted.

## Security

Unless --key option is given, the client will be restricted to the same host (this check may have nonsense behind proxy).

It is recommended to use --key option to set key-based access and also to use https proxy if you serve via network.

## Install

```
python3 -m venv venv
. venv/bin/activate
pip install llama-cpp-python
mkdir models
```

Download llama.cpp compatible model into models/.
For example any GGUF from https://huggingface.co/TheBloke

For Russian language check https://huggingface.co/IlyaGusev/saiga2_13b_gguf

For a good experience I suggest to use at least 13B models, quantized to at least 3bits (4 bits will be a bit better :).

## Model conversation templates

When using Llama2-chat model, specify "-s chat" in command line.
Otherwise the Saiga format will be used.
The formatters are custom (not library ones) for the historical reasons.

## Run

Activate venv
```
. venv/bin/activate
```

Then
```
python aicom_llamacpp.py -m models/YOUR__MODEL.gguf
```

For Metal (Apple M1, M2) GPU run
```
python aicom_llamacpp.py -m models/YOUR__MODEL.gguf --n_gpu_layers=1
```

For help on parameters
```
python aicom_llamacpp.py -h
```

## Examples

Llama2-chat on Mac with access key
```
python aicom_llamacpp.py -k secret -m models/13B/llama-2-13b-chat.Q4_K_M.gguf --n_gpu_layers=1 -s chat
```

Saiga on Mac with access key
```
python aicom_llamacpp.py -k secret -m models/13B/ggml-model-q4_K.gguf --n_gpu_layers=1
```
