# Code Structure
`wiki-search.py` Wikipedia Search tool using MediaWiki API
`answer-engine.py` Interactive CLI tool to get answers for questions using Claude Haiku and the Wikipedia Search tool
`batch-answers.py` Non interactive answer generation using the implementation in `answer-engine.py`
`llm-judge.py` Judge whether provided ("golden label") is better than generated answer
`evaluation.py` Generate metrics based on judgements from the LLM-judge; Also summarize the judge's rationale.
`extract-positives.py` Extract only positives from WikiQA dataset. We don't consider negative labels here.

# Prompts
`system-prompt.md`: Main prompt to produce answer using the Wiki search tool.
`system-prompt-is-wiki.md`: To decide whether the input is anwerable using Wikipedia content
`llm-judge-system-prompt.md`: Guidelines for the llm-as-judge 


# Iteration Loop
   * Strictly iterate only on development / validation sets
   * Prepare a slice of dev/validation set using:
```bash
python3 extract-positives.py <input.tsv> <output.tsv>
```
Obtain a baseline on development set
```bash
python3 batch-answers.py <input.tsv> <answers.tsv>
python3 llm-judge.py <answers.tsv> <judged.json>
python3 evaluation.py <judged.json> --summary --judgement FALSE
```
This will output the metrics as:
```
Total records              : ...
GeneratedAnswerPreferred   : xx%  (n)
ProvidedAnswersPreferred   : yy%  (m)
Tie                        : xx%  (q)
Neither                    : tt%  (r)

Summary of rationales for Judgement=FALSE: ...
```
   * Analyze the explanation on why the GeneratedAnswers are not preferred
   * Manually spot check a few (Question,ProvidedAnswer,GeneratedAnwer) tuples to form an intuition on what can be fixed
   * Update the prompts and/or code
   * Rerun the evaluation
   * The evaluation steps are in captured in `eval.sh` for repeated execution.
   * Execute the script as
```bash
bash eval.sh input.tsv run_name
```
Of course, don't forget to tune the prompt(s) and/or code to address the observations from the run. 