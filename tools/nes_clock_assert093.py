# SPDX-License-Identifier: MIT
"""Conservative, clock-independent propagation graph from Quartus VO/SDF.

This is an assertion-delay inventory, not a logic simulator or board signoff.
Only combinational arcs and asynchronous clrn->q arcs may propagate. Clocked
FF arcs, PLLs and RAM are barriers. Rise/fall/max values are deliberately
over-approximated; paths need not be sensitizable. All arithmetic is integer ps.
"""
from pathlib import Path
from collections import defaultdict, deque
import argparse, hashlib, json, re

SOURCES = ['clock_guard|ref_fault', 'clock_guard|mem_fault',
           'clock_guard|ref_qualified', 'clock_guard|mem_qualified']
CONTROLS = ['ROM_1CE', 'ROM_2CE', 'ROM_OE', 'ROM_WE', 'ROM_BHE', 'ROM_BLE']
TARGETS = CONTROLS + [f'ROM_DATA[{i}]' for i in range(16)]
COMB = {'cycloneive_lcell_comb', 'cycloneive_io_obuf'}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sexpr(text):
    text = re.sub(r'//[^\n]*', '', text)
    tokens = re.findall(r'"[^"\n]*"|[()]|[^\s()]+', text)
    root = []; stack = [root]
    for token in tokens:
        if token == '(':
            item = []; stack[-1].append(item); stack.append(item)
        elif token == ')':
            assert len(stack) > 1, 'unbalanced SDF'
            stack.pop()
        else:
            stack[-1].append(token.strip('"'))
    assert len(stack) == 1 and len(root) == 1
    return root[0]


def normalized(value):
    return re.sub(r'\s+', '', value.replace('\\', '').lstrip('!'))


def delay(values):
    numbers = []
    for value in values:
        assert isinstance(value, list) and len(value) == 1, value
        triple = value[0].split(':')
        assert len(triple) == 3 and all(re.fullmatch(r'\d+', x) for x in triple), value
        numbers.extend(map(int, triple))
    assert numbers
    return max(numbers)


def parse(vo, sdf):
    instances = {}
    for m in re.finditer(r'^(dffeas|cycloneive_\w+)\s+(\\\S+|\w+)\s*\((.*?)\);',
                         vo.read_text(), re.M | re.S):
        kind, name, body = m.groups(); name = normalized(name)
        ports = dict(re.findall(r'\.(\w+)\(([^()]*)\)', body))
        assert name not in instances
        instances[name] = (kind, {p: normalized(v) for p, v in ports.items()})
    tree = sexpr(sdf.read_text()); assert tree[0] == 'DELAYFILE'
    assert ['TIMESCALE', '1', 'ps'] in tree, 'Only integer ps SDF supported'
    cells = {}; edges = []; async_cells = []
    for cell in tree[1:]:
        if cell[0] != 'CELL':
            continue
        fields = {x[0]: x[1:] for x in cell[1:]}
        name = normalized(fields['INSTANCE'][0]); kind = fields['CELLTYPE'][0]
        assert name not in cells; cells[name] = fields
        if kind not in COMB | {'dffeas'}:
            continue
        assert name in instances and instances[name][0] == kind, name
        ports = instances[name][1]
        blocks = fields['DELAY']; assert len(blocks) == 1 and blocks[0][0] == 'ABSOLUTE'
        rows = blocks[0][1:]; pdelay = {}; arcs = []
        for row in rows:
            assert row[0] in {'PORT', 'IOPATH'}, row
            if row[0] == 'PORT':
                assert row[1] not in pdelay
                pdelay[row[1]] = delay(row[2:])
            else:
                pin = row[1][-1] if isinstance(row[1], list) else row[1]
                if kind == 'dffeas':
                    if pin != 'clrn':
                        continue  # No propagation through clk, d or asdata.
                    assert row[1] == ['negedge', 'clrn'] and row[2] == 'q'
                    async_cells.append(name)
                else:
                    assert isinstance(row[1], str), row
                arcs.append((pin, row[2], delay(row[3:])))
        if kind == 'dffeas' and ports.get('clrn') not in {'vcc', 'gnd', '', None}:
            assert any(a[0] == 'clrn' for a in arcs), 'MISSING_ASYNC_ARC ' + name
        for src, dst, cell_ps in arcs:
            assert src in ports and dst in ports, (name, src, dst)
            a, b = ports[src], ports[dst]
            if not a or not b or a in {'vcc', 'gnd'}:
                continue
            # Accept only single nets, optional inversion and escaped bit select.
            assert re.fullmatch(r'[\w|~\[\].]+', a) and re.fullmatch(r'[\w|~\[\].]+', b), (a, b)
            # Absent PORT annotation leaves the generated zero-delay net
            # connection unchanged. Report that explicitly in each path.
            route_ps = pdelay.get(src, 0)
            edges.append(dict(src=a, dst=b, ps=route_ps+cell_ps,
                              route_ps=route_ps, port_annotated=src in pdelay, cell_ps=cell_ps,
                              instance=name, kind=kind, arc=src+'->'+dst))
    assert instances and cells
    for name in ['boundary|memory_release[0]', 'boundary|memory_release[1]',
                 'boundary|loader|boot|reader|reading_active']:
        assert name in async_cells, 'MISSING_ASYNC_ARC ' + name
    # Every used combinational/asynchronous instance must have SDF, even if an
    # alternate path would otherwise mask an omitted cell.
    for name, (kind, ports) in instances.items():
        if kind not in COMB | {'dffeas'} or name in cells:
            continue
        inputs = ['i', 'oe'] if kind == 'cycloneive_io_obuf' else ['dataa', 'datab', 'datac', 'datad', 'cin']
        assert kind != 'dffeas' and all(ports.get(p) in {'gnd', 'vcc'} for p in inputs), 'MISSING_CELL ' + name
    return instances, edges, async_cells


def longest(instances, edges, source):
    start = instances[source][1]['q']; adj = defaultdict(list)
    for i, edge in enumerate(edges):
        adj[edge['src']].append(i)
    reach = {start}; queue = deque([start])
    while queue:
        for i in adj[queue.popleft()]:
            node = edges[i]['dst']
            if node not in reach:
                reach.add(node); queue.append(node)
    indegree = dict.fromkeys(reach, 0)
    for edge in edges:
        if edge['src'] in reach:
            indegree[edge['dst']] += 1
    queue = deque(n for n, count in indegree.items() if count == 0)
    distance = {start: 0}; previous = {}; visited = 0
    while queue:
        node = queue.popleft(); visited += 1
        for i in adj[node]:
            edge = edges[i]; dst = edge['dst']
            if node in distance and distance[node]+edge['ps'] > distance.get(dst, -1):
                distance[dst] = distance[node]+edge['ps']; previous[dst] = i
            indegree[dst] -= 1
            if indegree[dst] == 0:
                queue.append(dst)
    assert visited == len(reach), 'ASYNC_GRAPH_CYCLE'
    results = []
    for target in TARGETS:
        assert target in distance, 'UNREACHABLE ' + source + ' -> ' + target
        path = []; node = target
        while node != start:
            edge = edges[previous[node]]; path.append(edge); node = edge['src']
        path.reverse()
        assert any(e['instance'] == 'boundary|memory_release[1]' and e['arc'] == 'clrn->q' for e in path)
        results.append(dict(source=source, target=target, maximum_ps=distance[target], path=path))
    return results


def analyze(vo, sdf):
    instances, edges, async_cells = parse(vo, sdf)
    paths = [p for source in SOURCES for p in longest(instances, edges, source)]
    assert all(e['port_annotated'] for p in paths for e in p['path']), 'UNANNOTATED_CRITICAL_ROUTE'
    maximum = max(p['maximum_ps'] for p in paths)
    # Structural fault-Q propagation allocation, not a measured electrical limit.
    assert maximum < 100000, 'PROPAGATION_ALLOCATION_EXCEEDED'
    return dict(vo_sha256=digest(vo), sdf_sha256=digest(sdf), paths=paths,
                instances=len(instances), sdf_async_cells=len(async_cells), arcs=len(edges),
                maximum_ps=maximum, allocation_ps=100000, external_signoff=False,
                logic_sensitization_proven=False, sdf_simulation_run=False,
                scope='Fault/qualification Q to PSRAM controls and data output; combinational + clrn only')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for n in ['vo', 'sdf', 'out']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args(); assert not a.out.exists()
    result = analyze(a.vo, a.sdf)
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('PASS assertion graph paths='+str(len(result['paths']))+' maximum_ps='+str(result['maximum_ps']))
