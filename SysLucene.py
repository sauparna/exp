import sys, os, subprocess
import simplejson as json
from bs4 import BeautifulSoup

class SysLucene():

    def __init__(self, path):
        self.path        = path
        self.model_file  = os.path.join(self.path["LUCENE"], "mods/models.lucene")
        self.model_map   = json.loads(open(self.model_file, "r").read())
        self.stemmer_map = {"porter"  : "PorterStemFilter",
                            "krovetz" : "KStemFilter", 
                            "snowball": "SnowballFilter",
                            "s"       : "EnglishMinimalStemFilter"}
        self.lib         = os.path.join(self.path["LUCENE"], "lib/*")

    def index(self, itag, doc, opt):
        
        # print(itag)

        stop_f  = "None"
        stemmer = "None"
        if opt[0] != "":
            stop_f = opt[0]
        if opt[1] in self.stemmer_map:
            stemmer = self.stemmer_map[opt[1]]

        o_dir = os.path.join(self.path["INDEX"], itag)

        if os.path.exists(o_dir):
            print("index(): found, so skipping " + itag)
            return

        #java -cp "lucene-5.3.1/trec/lib/*:lucene-5.3.2/trec/bin/TREC.jar" IndexTREC 
        #-docs doc/

        output = ""
        
        try:
            output = subprocess.check_output(["java",
                                           "-Xmx2048m",
                                           "-cp",       self.lib,
                                           "IndexTREC",
                                           "-index",    o_dir,
                                           "-docs",     doc,
                                           "-stop",     stop_f,
                                           "-stem",     stemmer],
                                          stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = str(e.cmd) + "\n" + str(e.returncode) + "\n" + str(e.output)

        o_log = os.path.join(os.path.join(self.path["LOG"], itag + ".i"))
        with open(o_log, "w+") as f:
            f.write(str(output))


    def retrieve(self, itag, rtag, opt, m, q, qe):

        # NOTE: Unused parameters 'opt' and 'qe'. Kept to maintain
        # parity with other system retrieve() calls. Haven't figured
        # how to do query-expansion in Lucene.

        # print(rtag)

        stop_f  = "None"
        stemmer = "None"
        if opt[0] != "":
            stop_f = opt[0]
        if opt[1] in self.stemmer_map:
            stemmer = self.stemmer_map[opt[1]]
        
        i_dir  = os.path.join(self.path["INDEX"], itag)
        i_file = q
        o_file = os.path.join(self.path["RUNS"], rtag)

        if not os.path.exists(i_dir):
            print("retrieve(): didn't find index " + itag)
            return

        if os.path.exists(os.path.join(o_file)):
            print("retrieve(): found, so skipping " + rtag)
            return

        #java -cp "bin:lib/*" BatchSearch -index /path/to/index 
        #-queries /path/to/queryfile -simfn default > default.out

        output = ""
        
        try:
            output = subprocess.check_output(
                        ["java",
                         "-cp",         self.lib,
                         "BatchSearch",
                         "-index",      i_dir,
                         "-queries",    i_file,
                         "-similarity", self.model_map[m[0]],
                         "-stop",       stop_f,
                         "-stem",       stemmer
                        ]
                    )
            with open(o_file, "w+b") as f:
                f.write(output)
        except subprocess.CalledProcessError as e:
            output = str(e.cmd) + "\n" + str(e.returncode) + "\n" + str(e.output)
            o_log = os.path.join(os.path.join(self.path["LOG"], rtag + ".r"))
            with open(o_log, "w+") as f:
                f.write(str(output))


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

        output = ""

        try:
            output = subprocess.check_output(
                [os.path.join(self.path["TRECEVAL"], "trec_eval"),
                 "-q", 
                 qrels,
                 i_file])
            with open(o_file, "w+b") as f:
                f.write(output)
        except subprocess.CalledProcessError as e:
            output = str(e.cmd) + "\n" + str(e.returncode) + "\n" + str(e.output)
            o_log = os.path.join(os.path.join(self.path["LOG"], rtag + ".e"))
            with open(o_log, "w+") as f:
                f.write(str(output))
