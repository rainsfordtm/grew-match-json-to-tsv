#!/usr/bin/python3
#######################################################################
# Quick script to generate .tsv files from Grew output, as with the
# GREW match online platform
#######################################################################

import argparse, glob, json, os.path, re, sys

def get_corpora_from_json(path):
    l = []
    json = parse_json(path)
    # Loop through the corpus
    for corpus in json:
        try:
            l.append(corpus['id'])
        except KeyError:
            # Can't read the JSON
            print('Could not find "id" entry in {}'.format(path))
            sys.exit(2)
            # Allow FileNotFound errors to be raised.
    return l

def get_conllus_from_json(path, corpus_id):
    l = []
    json = parse_json(path)
    # Loop through the corpus
    for corpus in json:
        try:
            l += [
                os.path.join(corpus['directory'], x)
                for x in glob.glob(
                    '*.conll*',
                    root_dir=corpus['directory']
                )
            ]
        except KeyError:
            # Can't read the JSON
            print('Could not find "directory" entry in {}'.format(path))
            sys.exit(2)
            # Allow FileNotFound errors to be raised.
    return l

def parse_conllu(conllu_file):
    
    def write_buff():
        nonlocal d, sent_id, buff
        if not sent_id:
            # Create GREW-style sent_id
            sent_id = '{}_{:0>5}'.format( 
                os.path.basename(conllu_file),
                len(d.keys()) + 1
            )
        d[sent_id] = buff
        sent_id, buff = '', {}
    
    with open(conllu_file, 'r', encoding='utf-8') as f:
        buff, d, sent_id = {}, {}, ''
        for line in f.readlines():
            # Empty line: write contents to dictionary
            if line.isspace() and buff: write_buff() # Empty line, write buffer
            # Line contains a sentence_id
            m = re.match(r'#\s*sent_id\s*=\s*([^\n]*)', line)
            if m: sent_id = m.group(1)
            # Line contains token
            m = re.match(r'([0-9\-\.]+)\t([^\t]+)\t', line)
            if m: buff[m.group(1)] = m.group(2) # ID, WORD entry in dictionary
        if buff: write_buff() # just in case file doesn't end with an empty line
    return d
            
def parse_json(json_file):
    with open(json_file) as f:
        return json.load(f)
        
def main(corpus, json, pivot, output=''):
    
    def write_hits():
        nonlocal corpus_id, conllus, hits, f
        for conllu in conllus:
            text = parse_conllu(conllu)
            id_prefix = corpus_id + '/' + os.path.basename(conllu) if corpus_id else ''
            for hit in hits:
                try:
                    f.write('\t'.join(write_hit(hit, text, id_prefix)) + '\n')
                except KeyError: # Raised by subroutine if hit isn't found.
                    pass
    
    def write_hit(hit, text, id_prefix):
        nonlocal pivot
        sid = hit['sent_id']  # ID from json file
        l = [id_prefix + '_' + sid] if id_prefix else [sid]
        # THIS RAISES A KEY ERROR IF THE HIT ISN'T FOUND.
        # HANDLED IN MAIN ROUTINE.
        sentence = text[sid]
        try:
            pivot_id = hit['matching']['nodes'][pivot]
        except KeyError:
            l.append('Pivot not in JSON')
            return l
        s_keys = list(sentence.keys())
        s_values = list(sentence.values())
        try:
            pivot_ix = s_keys.index(pivot_id)
        except ValueError:
            l.append('Pivot ID not in text')
            return l
        try:
            l += [' '.join(s_values[:pivot_ix]),
                s_values[pivot_ix],
                ' '.join(s_values[pivot_ix + 1:])
            ]
        except IndexError: # pivot is last word in sentence
            l += [
                ' '.join(s_values[:pivot_ix]),
                s_values[pivot_ix],
                ''
            ]
        return l

    # Set name for output file
    if not output: output = json[:-4] + 'tsv' # Default outfile simply replaces the JSON extension with .tsv
    # Load results file
    results = parse_json(json)
    # Detect if multi or mono mode
    ext = os.path.splitext(corpus)
    with open(output, 'w', encoding='utf-8') as f:
        if ext[1] == '.json':
            # Multi mode
            corpora = get_corpora_from_json(corpus)
            for corpus_id in corpora:
                conllus = get_conllus_from_json(corpus, corpus_id)
                hits = results[corpus_id]
                write_hits()
        else:
            # Mono mode
            hits = results
            conllus = [corpus]
            corpus_id = ''
            write_hits()
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description = \
        'Converts grew grep JSON file into a .tsv file.'
    )
    parser.add_argument('--corpus', help='Source corpus file, either .conllu (MONO) or .json (MULTI)', required=True)
    parser.add_argument('--json', help='JSON file with matches.', required=True)
    parser.add_argument('--pivot', help='Name of pivot node.', required=True)
    parser.add_argument('--output', help='Output file.')
    kwargs = vars(parser.parse_args())
    main(**kwargs)
    
