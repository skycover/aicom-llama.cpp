from llama_cpp import Llama
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import argparse

SYSTEM_TOKEN = 1788
USER_TOKEN = 1404
BOT_TOKEN = 9225
LINEBREAK_TOKEN = 13

ROLE_TOKENS = {
    "user": USER_TOKEN,
    "bot": BOT_TOKEN,
    "system": SYSTEM_TOKEN
}


def get_message_tokens(model, role, content):
    message_tokens = model.tokenize(content.encode("utf-8"))
    message_tokens.insert(1, ROLE_TOKENS[role])
    message_tokens.insert(2, LINEBREAK_TOKEN)
    message_tokens.append(model.token_eos())
    return message_tokens


# example only
def get_system_tokens(model, prompt):
    system_message = {
        "role": "system",
        "content": prompt
    }
    return get_message_tokens(model, **system_message)

def tokenize_context(model, mwssages):
    tokens = []
    for (role, content) in mwssages:
        tokens += get_message_tokens(model, role, content)
    return tokens

model = ''
tokens = []
args = {}

def interact():
    global model, args

    model = Llama(
        model_path=args.model,
        n_ctx=args.n_ctx,
        n_parts=1,
        n_gpu_layers=args.n_gpu_layers,
    )

    server = HTTPServer((args.host, args.port), HttpHandler)
    print(f"Starting server at {args.host}:{+args.port}, use Ctrl+C to stop")
    server.serve_forever()


class HttpHandler(BaseHTTPRequestHandler):
    def send_reply(self, code, message):
        print("\n", code, message)
        self.send_response(code)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(message.encode())

    def do_POST(self):
        global model, args, generator, tokens
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
                role_tokens = [model.token_bos(), BOT_TOKEN, LINEBREAK_TOKEN]
                tokens += tokens + role_tokens
                generator = model.generate(
                    tokens,
                    top_k = pquery['params'].get('top_k', args.top_k),
                    top_p = pquery['params'].get('top_p', args.top_p),
                    temp = pquery['params'].get('temperature', args.temperature),
                    repeat_penalty = pquery['params'].get('repeat_penalty', args.repeat_penalty)
                )
                self.send_reply(200, str(len(tokens)))
            except json.JSONDecodeError as e:
                self.send_reply(400, e.msg)
                
        else:
            self.send_reply(404,'not found')

    def do_GET(self):
        global model, generator
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
            tokens.append(token)
            if token == model.token_eos():
                self.send_reply(200, '[[END OF AICOM SENTENCE]]')
                return

            self.send_reply(200, token_str)

        else:
            self.send_reply(404,'not found')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model', required=True, help='model pathname')
    parser.add_argument('-l', '--host', required=False, default='127.0.0.1', help='listen IP address (not DNS name)')
    parser.add_argument('-p', '--port', required=False, type=int, default=8080, help='listen port')
    parser.add_argument('-k', '--key', required=False, default='', help='secret key')
    parser.add_argument('--n_ctx', required=False, type=int, default=2000, help='context size')
    parser.add_argument('--top_k', required=False, type=int, default=30)
    parser.add_argument('--top_p', required=False, type=float, default=0.9)
    parser.add_argument('--temperature', required=False, type=float, default=0.2)
    parser.add_argument('--repeat_penalty', required=False, type=float, default=1.1)
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
