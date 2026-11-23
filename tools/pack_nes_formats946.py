"""Drop unused report dictionary text, retaining every token index and expansion."""
import ast
import re

from prepare_nes_report594 import literal


def compact(src):
    budget=(src/'nes_budget210.c').read_text()
    table=ast.literal_eval(re.search(r'static const char words\[\] = (".*?");',budget)[1])
    words=[s.encode('latin1') for s in table.split('\0')[:-1]]
    # Keep token indices stable. A zero-length entry still has its separator.
    pattern=r'"(?:[^"\\]|\\.)*"'
    declaration=re.search(r'static const char words\[\] = (".*?");',budget)
    literals=[]
    for name in ('nes_budget210.c','nes_cost471.c','nes_menu_diagnostic.c','nes_cost471.h'):
        code=(src/name).read_text().replace(declaration[0],'')
        for token in re.findall(pattern,code):
            if re.search(r'\\[23][0-7][0-7]',token):
                literals.append(ast.literal_eval(token).encode('latin1'))
    used={b-128 for token in literals for b in token if b>=128}
    assert used and max(used)<len(words)
    reduced=[w if i in used else b'' for i,w in enumerate(words)]
    def expanded(table,token):
        return b''.join(bytes([b]) if b<128 else table[b-128] for b in token)
    assert all(expanded(words,t)==expanded(reduced,t) for t in literals)
    new='static const char words[] = '+literal(b'\0'.join(reduced)+b'\0')+';'
    (src/'nes_budget210.c').write_text(budget.replace(declaration[0],new),newline='\n')
    return sum(map(len,words))-sum(map(len,reduced))
