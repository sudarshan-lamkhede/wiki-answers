#!bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 input_tsv run_name"
    exit 1
fi

INPUT_TSV=$1
RUN_NAME=$2
ANSWER_TSV=$2".answers.tsv"
JUDGED_TSV=$2".judged.json"

echo "\n`date`: Generating answers..."
python3 batch-answers.py $INPUT_TSV $ANSWER_TSV

echo "\n`date`: Judging the genereated answers..."
python3 llm-judge.py $ANSWER_TSV $JUDGED_TSV

echo "\n`date`: Evaluating and thinking about why generated answers aren't better in some cases..."
python3 evaluation.py $JUDGED_TSV --summary --judgement FALSE
