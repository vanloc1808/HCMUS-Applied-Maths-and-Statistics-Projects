from collections import defaultdict
from nltk.corpus.reader import BracketParseCorpusReader
import glob
import string

NEAR_ZERO = 0.00000001

dataset_path = './dataset'
list_of_file = glob.glob(dataset_path + '/train/' + '/*.mrg') # Lấy đường dẫn toàn bộ file trong thư mục

reader_corpus = BracketParseCorpusReader('.', list_of_file)

# Đọc dữ liệu các câu
list_of_tagged_sents = reader_corpus.tagged_sents() 

def printSentence(tag_sent, word_per_line = 2):
    word_per_line = min(word_per_line, len(tag_sent) - 1)
    print('[', end='')
    for i in range(0, len(tag_sent)):
        if i % word_per_line == 0:
            print('')
            print('\t', end = '')
        print(tag_sent[i], end = ', ')
    print('\n]')


print("Du lieu ban dau:")
printSentence(list_of_tagged_sents[0])

# Lọc bỏ những từ không có tag (-NONE-)
list_of_tagged_sents = list(map(
    lambda sent: list(filter(
        lambda word: word[1] != '-NONE-',
        sent
    )),
    list_of_tagged_sents
))

# Chuyển đổi tag dấu câu thành SYM
list_of_tagged_sents = list(map(
    lambda sent: list(map(
        lambda word: (word[0], "SYM") if word[1][0] in string.punctuation else word,
        sent
    )),
    list_of_tagged_sents
))
print("Ket Qua sau khi loc: ")
printSentence(list_of_tagged_sents[0])

# Vd bigram: [1,2,3,4] -> [(1,2), (2,3), (3,4)]
# C(t_{i-1}, t_i)
def bigramCount(tag_sent_list):
    # Tạo bigram trên tag
    # Bigram được tạo riêng trên mỗi câu!

    bigram = [
        (sent[i][1], sent[i + 1][1]) for sent in tag_sent_list for i in range(len(sent) - 1)
    ]

    map_count = defaultdict(lambda: NEAR_ZERO)
    for x in bigram:
        if x in map_count:
            map_count[x] += 1
        else:
            map_count[x] = 1
    return map_count

# Tương tự với unigram
# C(t_i)
def unigramCount(tag_sent_list):
    unigram = [
        word[1] for sent in tag_sent_list for word in sent
    ]
    map_count = defaultdict(lambda: NEAR_ZERO)
    for x in unigram:
        if x in map_count:
            map_count[x] += 1
        else:
            map_count[x] = 1
    return map_count

def wordtagCount(tag_sent_list):
    map_count = defaultdict(lambda: NEAR_ZERO)
    for sent in tag_sent_list:
        for word in sent:
            if word in map_count:
                map_count[word] += 1
            else:
                map_count[word] = 1
    return map_count

# Tính P(t_{i} | t_{i - 1})
def Ptt(bi_cnt, uni_cnt, tag1, tag2):
    return bi_cnt[(tag1, tag2)] / uni_cnt[tag1]

# Tính P(w_i | t_i)
def Pwt(wt_cnt, uni_cnt, tag, word):
    count1 = wt_cnt[(word, tag)]
    count2 = uni_cnt[tag]
    return count1 / count2

# Tagset (36 loại)
tag_set = [
    'JJS', 'PRP$', 'WDT', 'NNP', 'TO', 'PDT', 'WRB', 'WP', 'NNS', 'VB', 'MD', 'RP', 
    'PRP', 'JJR', 'JJ', 'VBZ', 'RBS', 'VBG', 'POS', 'VBD', 'NN', 'UH', 'FW', 'NNPS', 
    'WP$', 'EX', 'SYM', 'RBR', 'VBN', 'LS', 'IN', 'DT', 'VBP', 'CD', 'RB', 'CC'
]

bi_cnt = bigramCount(list_of_tagged_sents)
uni_cnt = unigramCount(list_of_tagged_sents)
wt_cnt = wordtagCount(list_of_tagged_sents)

def transition_matrix(tag_set, bi_cnt, uni_cnt):
    A = {}
    for tag1 in tag_set:
        for tag2 in tag_set:
            A[(tag1, tag2)] = Ptt(bi_cnt, uni_cnt, tag1, tag2)
            # Normalize: < ZERO -> ZERO
            if A[(tag1, tag2)] < NEAR_ZERO:
                A[(tag1, tag2)] = NEAR_ZERO
    return A

A = transition_matrix(tag_set, bi_cnt, uni_cnt)

def emission_matrix(tag_sent_list, tag_set, uni_cnt, wt_cnt):
    word_set = []
    for sent in tag_sent_list:
        for word in sent:
            word_set.append(word[0])
    word_set = list(set(word_set)) # Loại bỏ từ trùng

    B = defaultdict(lambda: NEAR_ZERO)
    for tag in tag_set:
        for word in word_set:
            B[(word, tag)] = Pwt(wt_cnt, uni_cnt, tag, word)
    return B
B = emission_matrix(list_of_tagged_sents, tag_set, uni_cnt, wt_cnt)

# Tính pi(t_i)
def pi_vector(tag_sent_list, tag_set):
    first_tag_cnt = defaultdict(lambda: NEAR_ZERO)
    for sent in tag_sent_list:
        first_tag = sent[0][1]
        if first_tag in first_tag_cnt:
            first_tag_cnt[first_tag] += 1
        else:
            first_tag_cnt[first_tag] = 1
    sent_cnt = len(tag_sent_list)

    vec = defaultdict(lambda: NEAR_ZERO)
    for tag in tag_set:
        vec[tag] = first_tag_cnt[tag] / sent_cnt
        # Normalization
        if vec[tag] < NEAR_ZERO:
            vec[tag] = NEAR_ZERO
    return vec

obs = ["every", "day", "there", "is", "much", "work", "to", "be" ,"done", "."]
pi = pi_vector(list_of_tagged_sents, tag_set)

# Thuật toán Viterbi trên quan sát, trả về tập quan sát cùng với nhãn dán.
def viterbi(obs, tag_set, A, B, pi):
    vit_matrix = defaultdict(lambda: NEAR_ZERO)
    bck_ptr = defaultdict(lambda: NEAR_ZERO)

    # Initial state:
    for tag in tag_set:
        vit_matrix[(tag, 0)] = pi[tag] * B[(obs[0], tag)]
        bck_ptr[(tag, 0)] = (tag, 0)
    
    for t in range(1, len(obs)):
        for tag in tag_set:
            x = 0
            for tag_before in tag_set:
                tmp = vit_matrix[(tag_before, t - 1)] * A[(tag_before, tag)] * B[(obs[t], tag)]
                if tmp > x:
                    x = tmp
                    bck_ptr[(tag, t)] = (tag_before, t - 1)
            vit_matrix[(tag, t)] = x
    
    m = 0
    b = None
    for tag in tag_set:
        if vit_matrix[(tag, len(obs) - 1)] > m:
            m = vit_matrix[(tag, len(obs) - 1)]
            b = (tag, len(obs) - 1)
    
    result = []

    while b[1] != 0:
        result.append((obs[b[1]], b[0]))
        b = bck_ptr[b]
    result.append((obs[b[1]], b[0]))
    return result[::-1]

print("Doan van ban ban dau:")
print(obs)
print("Sau khi dan nhan:")
print(viterbi(obs, tag_set, A, B, pi))
print("Danh gia mo hinh")

# ===============================================================

list_of_file = glob.glob(dataset_path + '/test/' + '/*.mrg') # Lấy đường dẫn toàn bộ file trong thư mục

reader_corpus = BracketParseCorpusReader('.', list_of_file)

# Đọc dữ liệu các câu
list_of_tagged_sents = reader_corpus.tagged_sents()
# Lọc bỏ những từ không có tag (-NONE-)
list_of_tagged_sents = list(map(
    lambda sent: list(filter(
        lambda word: word[1] != '-NONE-',
        sent
    )),
    list_of_tagged_sents
))

# Chuyển đổi tag dấu câu thành SYM
list_of_tagged_sents = list(map(
    lambda sent: list(map(
        lambda word: (word[0], "SYM") if word[1][0] in string.punctuation else word,
        sent
    )),
    list_of_tagged_sents
))

def calc_accuracy_sentence(sent, tag_set, A, B, pi):
    obs = [word[0] for word in sent] # Tách phần chữ
    result = viterbi(obs, tag_set, A, B, pi)

    correct = 0
    assert(len(result) == len(sent))
    for i in range(len(result)):
        if (sent[i] == result[i]):
            correct += 1
    return correct / len(sent)

import statistics

acc_list = [calc_accuracy_sentence(sent, tag_set, A, B, pi) * 100 for sent in list_of_tagged_sents]
print(f"Do chinh xac cao nhat: {max(acc_list):.4f}%")
print(f"Do chinh xac thap nhat: {min(acc_list):.4f}%")
print(f"Trung binh: {statistics.mean(acc_list):.4f}%")
print(f"Phuong sai: {statistics.variance(acc_list):.4f}")