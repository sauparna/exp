import sys, os, subprocess
from bs4 import BeautifulSoup

#indri-5.0/buildindex/IndriBuildIndex parameter_file
#-corpus.path=/path/to/file_or_directory
#-corpus.class=trectext
#-index=/path/to/repository
#-memory 100M
#-stopper.word=stopword
#-stemmer.name=stemmername
#-field.name=fieldname

#field : a complex element specifying the fields to index as data, eg
#TITLE. This parameter can appear multiple times in a parameter
#file. If provided on the command line, only the first field specified
#will be indexed.

#indri-5.0/runquery/IndriRunQuery query_parameter_file -count=1000 -index=/path/to/index -trecFormat=true > result_file
#-query="apple juice" or -query="#combine(apple juice)"

#TREC queries cannot be fed into Indri directly, punctuations need to
#be removed. One simple strategy is to replace everything that's not a
#number (0x30-0x39) or letter with a space (0x20). However,
#tokenization should be performed similar to how the indexer indexes
#texts. And in Indri, "U.S." will be translated into "us" in the
#indexer.

class SysIndri():


    def __init__(self, path):

        self.path = path
        self.stemmer_map = {"p": "porter", "k": "krovetz"}

    def __shapeup_xml(self, l):

        # The Indri parameters file must have absolute paths within
        # tags without any extraneous characters (like newlines) at
        # the ends of the string. This function makes it a point to
        # gather all tags and content within tags in one line for
        # everyhting that there is in the file. For an explanation
        # see:
        # http://sourceforge.net/p/lemur/discussion/2106523/thread/431e2048/

        l_ = []
        n = 0

        for i in range(len(l)):
            l[i] = l[i].lstrip().rstrip()
            l[i] = l[i].lstrip("\n").rstrip("\n")
            l_.append(l[i])
            n = len(l_) - 1

            if i == 0:
                continue

            if l_[n].startswith("</"):
                if not l_[n-1].startswith("<"):
                    e  = l_.pop()
                    e1 = l_.pop()
                    e2 = l_.pop()
                    l_.append(e2 + e1 + e)
                    n = len(l_) - 1
                
        return "\n".join(l_)
        

    def __index_params_file(self, itag, doc, o_dir, opt):
        
        # build and write Indri's index param file

        soup = BeautifulSoup("<parameters></parameters>", "xml")

        T_corpus = soup.new_tag("corpus")
        soup.parameters.append(T_corpus)

        T_path = soup.new_tag("path")
        T_path.string = doc
        soup.parameters.corpus.append(T_path)

        T_class = soup.new_tag("class")
        T_class.string = "trectext"
        soup.parameters.corpus.append(T_class)

        T_index = soup.new_tag("index")
        T_index.string = o_dir
        soup.parameters.append(T_index)

        # float 5 <field> tags in the soup
        TREC_field = ["TEXT", "H3", "DOCTITLE", "HEADLINE", "TTL"]
        i = 0
        for i in range(5):
            T_field = soup.new_tag("field")
            T_name = soup.new_tag("name")
            T_name.string = TREC_field[i]
            T_field.append(T_name)
            soup.parameters.append(T_field)
            i += 1

        # add stopfile
        if opt[0] != "None":
            T_stopwords = soup.new_tag("stopwords")
            T_stopwords.string = os.path.join(self.path["MISC"], opt[0])
            soup.parameters.append(T_stopwords)
            
        # add stemmer
        if opt[1] in self.stemmer_map:
            T_stemmer = soup.new_tag("stemmer")
            T_name = soup.new_tag("name")
            T_name.string = self.stemmer_map[opt[1]]
            T_stemmer.append(T_name)
            soup.parameters.append(T_stemmer)

        # purge the XML declaration introduced by BeautifulSoup and
        # shape it up for Indri to consume

        o_file = os.path.join(self.path["INDEX"], itag + ".indri")

        with open(o_file, "w") as f:
            f.write(self.__shapeup_xml(soup.prettify().split("\n")[1:]))

        return o_file

    def __query_params_file(self, rtag, q):

        # queries are in a dict q
        # build the query-param XML and write it out to disk

        soup = BeautifulSoup("<parameters></parameters>", "xml")

        # float n query tags in the soup

        for num in q:
            T_query = soup.new_tag("query")
            T_type = soup.new_tag("type")
            T_type.string = "indri"
            T_number = soup.new_tag("number")
            T_number.string = num
            T_text = soup.new_tag("text")
            T_text.string = "#combine(" + q[num] + ")"
            T_query.append(T_type)
            T_query.append(T_number)
            T_query.append(T_text)
            soup.parameters.append(T_query)

        o_file = os.path.join(self.path["RUNS"], rtag + ".indri")

        # purge the XML declaration introduced by BeautifulSoup and
        # shape it up for Indri to consume

        with open(o_file, "w") as f:
            f.write(self.__shapeup_xml(soup.prettify().split("\n")[1:]))

        return o_file

        
    def index(self, itag, doc, opt):

        # print(itag)

        o_dir  = os.path.join(self.path["INDEX"], itag)
        i_file = self.__index_params_file(itag, doc, o_dir, opt)
        log = ""

        if os.path.exists(o_dir):
            print("index(): found, so skipping " + itag)
            return
        
        try:
            log = subprocess.check_output([os.path.join(self.path["INDRI"], 
                                                        "bin/IndriBuildIndex"),
                                           i_file])
        except subprocess.CalledProcessError as e:
            log = str(e.cmd) + "\n" + str(e.returncode) + "\n" + str(e.output)
        
        o_log = os.path.join(os.path.join(self.path["INDEX"], itag + ".log"))
        with open(o_log, "w+b") as f:
            f.write(log)

    def retrieve(self, itag, rtag, opt, m, q):

        # NOTE: Unused parameters 'opt' and 'm'. Kept to maintain
        # parity with other system retrieve() calls.

        # print(rtag)

        # NOTE: Indri doesn't need to be told to stem query terms. If
        # the index is stemmed, the queries go through the same
        # stemmer. Below is a quote from David Fisher's response found
        # in the Indri forums. The documentation does not make this
        # clear.
        # http://sourceforge.net/p/lemur/discussion/836442/thread/0f00c8e5/
        # "If you stem your index when you build it, query terms are
        # automatically stemmed when the query is run. ..."
        
        i_dir = os.path.join(self.path["INDEX"], itag)
        i_file = self.__query_params_file(rtag, q)
        o_file = os.path.join(self.path["RUNS"], rtag)

        if not os.path.exists(i_dir):
            print("retrieve(): didn't find index " + itag)
            return

        if os.path.exists(os.path.join(o_file)):
            print("retrieve(): found, so skipping " + rtag)
            return

        with open(o_file, "w+b") as f:
            f.write(subprocess.check_output(
                    [os.path.join(self.path["INDRI"], "bin/IndriRunQuery"),
                     i_file,
                     "-index=" + i_dir,
                     "-count=1000",
                     "-trecFormat=true"]
                    ))
    
    def evaluate(self, rtag, qrels):

        # print(rtag)

        # trec_eval -q QREL_file Retrieval_Results > eval_output
        # call trec_eval and dump output to a file

        i_file = os.path.join(self.path["RUNS"], rtag)
        o_file = os.path.join(self.path["EVALS"], rtag)

        if not os.path.exists(i_file):
            print("evaluate(): didn't find run " + rtag)
            return

        if os.path.exists(o_file):
            print("evaluate(): found, so skipping " + rtag)
            return

        with open(o_file, "w+b") as f:
            f.write(subprocess.check_output(
                    [self.path["EVAL"],
                     "-q",
                     qrels,
                     i_file]))
