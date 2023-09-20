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

If you'll stop check, then the inference will stop and free memory till next request. Simple stop requests if you
don't want to get the rest of inference.

If you'll send a new /query, then inference will be restarted.

## Security

Unless --key option is given, the client will be restricted to the same host (may not work behind proxy).

We recommend to use --key option to set key-based access and also to use https proxy if you serve via network.

## Install

```
python3 -m venv venv
. venv/bin/activate
pip install llama-cpp-python
mkdir models
```

Download llama.cpp compatible model into models.
For example any GGUF from https://huggingface.co/TheBloke

For Russian language check https://huggingface.co/IlyaGusev/saiga2_13b_gguf

Run
```
python aicom_llamacpp.py -m models/YOUR__MODEL.gguf
```

For Metal (Apple M1, M2) GPU run
```
python aicom_llamacpp.py -m models/YOUR__MODEL.gguf --n_gpu_layers=1
```
