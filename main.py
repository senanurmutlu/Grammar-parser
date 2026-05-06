import json
grammar_file = "grammar2.txt"
sentences_file = "sentences2.txt"

def read_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def parse_grammar(lines):
    grammar = {}
    for line in lines:
        left, right = line.split("::=")
        left = left.strip()
        grammar[left] = [alt.strip().split() for alt in right.split("|")]
    return grammar

class ParseError(Exception):
    def __init__(self, message, index):
        super().__init__(message)
        self.index = index

class Node:
    def __init__(self, type_, children=None, value=None):
        self.type = type_
        self.children = children or []
        self.value = value

    def to_dict(self):
        if self.value is not None:
            return self.value
        return {
            child.type.strip("<>"): child.to_dict()
            for child in self.children
            if child.type != "epsilon"
        }

def detect_mode(grammar):
    if "<noun-phrase>" in grammar and "<verb-phrase>" in grammar:
        return "grammar1"
    return "generic"


def tokenize(sentence, mode):
    if sentence.lower() in ["ε", "epsilon", "boş string"]:
        return []

    if mode == "grammar1":
        return sentence.split()  # kelime bazlı
    else:
        return list(sentence.replace(" ", ""))  # karakter bazlı

def parse(symbol, grammar, tokens, index, mode):

    if symbol in ["ε", "epsilon"]:
        return Node("epsilon", value=""), index

    if mode == "grammar1" and symbol == "<sentence>":
        try:
            det_node, index = parse("<determiner>", grammar, tokens, index, mode)
            noun_node, index = parse("<noun>", grammar, tokens, index, mode)
            np_node = Node("<noun-phrase>", [det_node, noun_node])
        except ParseError as e:
            raise ParseError(
                "Sentence must start with a noun phrase (determiner + noun).",
                e.index
            )

        try:
            verb_node, index = parse("<verb>", grammar, tokens, index, mode)
        except ParseError as e:
            raise ParseError(
                "Verb phrase must follow noun phrase.",
                e.index
            )

        if index < len(tokens):
            try:
                np2, new_index = parse("<noun-phrase>", grammar, tokens, index, mode)
                index = new_index
                vp_node = Node("<verb-phrase>", [verb_node, np2])
            except ParseError:
                vp_node = Node("<verb-phrase>", [verb_node])
        else:
            vp_node = Node("<verb-phrase>", [verb_node])

        return Node("<sentence>", [np_node, vp_node]), index

    if symbol in grammar:
        best_error = None

        for alt in grammar[symbol]:
            i = index
            children = []
            success = True

            for part in alt:
                try:
                    node, i = parse(part, grammar, tokens, i, mode)
                    children.append(node)
                except ParseError as e:
                    success = False
                    if best_error is None or e.index > best_error.index:
                        best_error = e
                    break

            if success:
                return Node(symbol, children), i

        raise ParseError(
            f"Invalid structure for {symbol}",
            best_error.index if best_error else index
        )

    if index < len(tokens) and tokens[index] == symbol:
        return Node(symbol, value=tokens[index]), index + 1

    found = tokens[index] if index < len(tokens) else "EOF"
    raise ParseError(f"Expected '{symbol}', found '{found}'", index)

grammar_lines = read_file(grammar_file)
sentences = read_file(sentences_file)

grammar = parse_grammar(grammar_lines)

start_symbol = "<sentence>" if "<sentence>" in grammar else list(grammar.keys())[0]

mode = detect_mode(grammar)

print("MODE:", mode)
print("\nGRAMMAR:")
print("\n".join(grammar_lines))

print("\nSENTENCES:")
print("\n".join(sentences))

for s in sentences:
    print("-" * 50)
    print("Input:", s)

    tokens = tokenize(s, mode)
    try:
        tree, idx = parse(start_symbol, grammar, tokens, 0, mode)

        if idx != len(tokens):
            raise ParseError("Extra tokens after valid structure", idx)

        print("Valid")
        print(json.dumps({start_symbol.strip("<>"): tree.to_dict()}, indent=2, ensure_ascii=False))

    except ParseError as e:
        token = tokens[e.index] if e.index < len(tokens) else "EOF"

        print("Invalid")
        print(f" • Error at token {e.index + 1} ('{token}')")
        print(f" • Reason: {str(e)}")