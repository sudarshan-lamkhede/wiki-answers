# TASK:
For a given question, decide if GeneratedAnswer is better than ProvidedAnwser.

An answer is better if it has the following characteristics:
   * Correctly answers the question per information in wikipedia
   * Satisfactorily answers the question considering the most likely information need behind the question
   * Contains all necessary information condensed in minimum number of words. it also avoids extra information not needed to satisfactorily answer the question. 
   * It is simple, understadable, clearly articulated. 

Only being correct is necessary but not sufficient for a good answer.
GeneratedAnswer is in Markdown format. Do not apply any penalty for the markdown syntax in the answer.

# INPUT
Format: JSON
Schema: {"Question": "", "ProvidedAnswer": "", "GeneratedAnswer": "", "ProvideRationale": true}

# OUTPUT
Format: JSON.

## Judgement
Output a single token as "Judgment":
   * "TRUE": GeneratedAnswer is better than ProvidedAnwser
   * "FALSE": ProvidedAnwser is better then GeneratedAnswer
   * "TIE": Both are equally good.
   * "NONE": Neither answers are good or valid.
## Rationale
Output a short, single sentence, rationale for the "Judgement" only if "ProvideRationale" is true. 

