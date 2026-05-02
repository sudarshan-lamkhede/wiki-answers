# TASK:
For a given question, decide if GeneratedAnswer is better than ProvidedAnwser.
An answer is better if it has both of the following characteristics:
   * Correctness: correctly answers the question per information in wikipedia
   * Conciseness: contains all necessary information but has no or minimum extra information that is not explicitly asked in the question. 
Only being correct is necessary but not sufficient for a good answer.

# INPUT
Format: JSON
Schema: {"Question": "", "ProvidedAnswer": "", "GeneratedAnswer": ""}

# OUTPUT
Format: JSON.

## Judgement
Output a single token as "Judgment":
   * "TRUE": GeneratedAnswer is better than ProvidedAnwser
   * "FALSE": ProvidedAnwser is better then GeneratedAnswer
   * "TIE": Both are equally good.
   * "NONE": Neither answers are good or valid.
## Rationale
Output a short, single sentence, rationale for the "Judgement" 

