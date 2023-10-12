from llama_cpp import Llama
from llama_cpp.llama_chat_format import format_llama2
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import argparse
from random import randint

SYSTEM_TOKEN = 1788
USER_TOKEN = 1404
BOT_TOKEN = 9225
LINEBREAK_TOKEN = 13

ROLE_TOKENS = {
    "user": USER_TOKEN,
    "bot": BOT_TOKEN,
    "system": SYSTEM_TOKEN
}

# chat template:
# <s>[INST] <<SYS>>\n{your_system_message}\n<</SYS>>\n\n{user_message_1} [/INST] {model_reply_1}</s><s>[INST] {user_message_2} [/INST]


def get_message_tokens_chat(model, role, content, was_system):
    if role == "system":
      if was_system: # bad condition, but let's handle
          message_tokens = model.tokenize((" [/INST]</s><s>[INST] <<SYS>>\n%s\n<</SYS>>" % content).encode('utf-9'), add_bos=False)
      else: # opening message
          message_tokens = model.tokenize(("[INST] <<SYS>>\n%s\n<</SYS>>" % content).encode('utf-8')) # add bos
    elif role == "user":
      if was_system: # append message to system
          message_tokens = model.tokenize(("\n\n%s [/INST]" % content).encode('utf-8'), add_bos=False)
      else: # start new message
          message_tokens = model.tokenize(("[INST] %s [/INST]" % content).encode('utf-8')) # add bos
    elif role == "bot":
      if was_system: # append message to system
          message_tokens = model.tokenize(("[/INST] %s </s>" % content).encode('utf-8'), add_bos=False) + [model.token_eos()]
      else: # append message to instruction
          message_tokens = model.tokenize((" %s " % content).encode('utf-8'), add_bos=False) + [model.token_eos()]

    return message_tokens

def print_tokens(tokens):
    for i in tokens:
        if i == model.token_bos():
            print('<BOS>', end='')
        elif i == model.token_eos():
            print('<EOS>', end='')
        else:
            print(model.detokenize([i]).decode("utf-8", errors="ignore")+'-', end='')
    print("")

# internal library tokenizer doesn't parse <s> and </s>
def tokenize_context_chat(model, messages):
    tokens = []
    was_system = False
    for (role, content) in messages:
        tokens += get_message_tokens_chat(model, role, content, was_system)
        was_system = role == "system"
    #print_tokens(tokens)
    print(model.detokenize(tokens).decode("utf-8", errors="ignore"))
    return tokens

def get_message_tokens_saiga(model, role, content):
    message_tokens = model.tokenize(content.encode("utf-8"))
    message_tokens.insert(1, ROLE_TOKENS[role])
    message_tokens.insert(2, LINEBREAK_TOKEN)
    message_tokens.append(model.token_eos())
    return message_tokens

def tokenize_context_saiga(model, messages):
    tokens = []
    for (role, content) in messages:
        tokens += get_message_tokens_saiga(model, role, content)
    role_tokens = [model.token_bos(), BOT_TOKEN, LINEBREAK_TOKEN]
    tokens += role_tokens
    return tokens

tokenize_context = tokenize_context_saiga
model = ''
args = {}

def interact():
    global model, args, tokenize_context

    if args.seed == -1:
        seed = randint(0, 2147483647)
        print('Generated seed:', seed)

    model = Llama(
        model_path=args.model,
        n_ctx=args.n_ctx,
        n_parts=1,
        n_gpu_layers=args.n_gpu_layers,
        seed = seed,
    )

    if args.template == 'chat':
        tokenize_context = tokenize_context_chat

    server = HTTPServer((args.host, args.port), HttpHandler)
    print(f"Starting server at {args.host}:{+args.port}, use Ctrl+C to stop")
    server.serve_forever()

first_token = True

class HttpHandler(BaseHTTPRequestHandler):
    def send_reply(self, code, message):
        print("\n", code, message)
        self.send_response(code)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(message.encode())

    def do_POST(self):
        global model, args, generator, first_token
        (host, port) = self.client_address;
        path = self.path

        if host != args.host:
            self.send_reply(503, 'Forbidden')

        elif path == '/':
            self.send_reply(200, 'Usage: query')

        elif path == '/query':
            # query: { {params}, [messages: (role, content)] }
            query = self.rfile.read1().decode('utf-8');
            print("\n GOT: ", query)
            try:
                pquery = json.loads(query)
                if args.key != '' and args.key != pquery.get('key',''):
                    self.send_reply(503, 'Forbidden')
                    return

                tokens = tokenize_context(model, pquery['messages'])
                first_token = True
                generator = model.generate(
                    tokens,
                    top_k = pquery['params'].get('top_k', args.top_k),
                    top_p = pquery['params'].get('top_p', args.top_p),
                    temp = pquery['params'].get('temperature', args.temperature),
                    repeat_penalty = pquery['params'].get('repeat_penalty', args.repeat_penalty),
                )
                self.send_reply(200, str(len(tokens)))
            except json.JSONDecodeError as e:
                self.send_reply(400, e.msg)
                
        else:
            self.send_reply(404,'not found')

    def do_GET(self):
        global model, generator, first_token
        (host, port) = self.client_address;
        urlreq = self.path.split("?")
        path = urlreq[0]
        key = ''
        if len(urlreq) > 1:
            key = urlreq[1]
        

        if args.key == '' and host != args.host:
            self.send_reply(503, 'Forbidden')

        elif args.key != '' and key != 'key='+args.key:
            self.send_reply(503, 'Forbidden')

        elif path == '/':
            self.send_reply(200, 'Usage: receive')

        elif path == '/receive':
            token = next(generator, '[[END OF AICOM OUTPUT]]')
            if token == '[[END OF AICOM OUTPUT]]':
                self.send_reply(200, '')
                return

            token_str = model.detokenize([token]).decode("utf-8", errors="ignore")
            #print(token, token_str)
            if token == model.token_eos():
                self.send_reply(200, '[[END OF AICOM SENTENCE]]')
                return

            if first_token and token == 29871:
                self.send_reply(200, '')
                return

            if first_token:
                self.send_reply(200, token_str.lstrip())
            else:
                self.send_reply(200, token_str)
            first_token = False

        else:
            self.send_reply(404,'not found')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model', required=True, help='model pathname')
    parser.add_argument('-t', '--template', required=False, default='saiga', help='syntax template: saiga, chat')
    parser.add_argument('-l', '--host', required=False, default='127.0.0.1', help='listen IP address (not DNS name)')
    parser.add_argument('-p', '--port', required=False, type=int, default=8080, help='listen port')
    parser.add_argument('-k', '--key', required=False, default='', help='secret key')
    parser.add_argument('--n_ctx', required=False, type=int, default=2000, help='context size')
    parser.add_argument('--top_k', required=False, type=int, default=30)
    parser.add_argument('--top_p', required=False, type=float, default=0.9)
    parser.add_argument('--temperature', required=False, type=float, default=0.2)
    parser.add_argument('--repeat_penalty', required=False, type=float, default=1.1)
    parser.add_argument('--seed', required=False, type=int, default=-1)
    parser.add_argument('--n_gpu_layers', required=False, type=int, default=0, help='set 1 for Metal (Apple M1,M2)')
    # defaults from 
    #top_k=40,
    #top_p=0.5,
    #temperature=0.7,
    #repeat_penalty=1.17
    #temperature=0.2,
    #n_gpu_layers=1

    args = parser.parse_args()
    interact()
