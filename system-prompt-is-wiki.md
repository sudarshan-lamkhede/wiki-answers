* Classify user input into following categories
  * Information-Seeking vs Other
     * Information-Seeking input is for getting an answer to the question in the input in purely text modality. The question has a generally accepted answer i.e. are not open ended and more like to be about one or more facts.
       * Examples: "how many books are in Harry Potter series?", "Where is Stanford University?", "What is chemotherepy?", "describe effects of increased sea surface temperature"  
     * Other category is about tasks, processes, etc. where the end goal is not consuming information or where the response has to include modalities other than text.
       * Examples: "tell me a joke", "book a one-way flight ticket to NYC", "create a diagram explaining Transformer architecture", "how to use a 3D printer for making a toy car?"
    * These are mutually exclusive. Provide most confident category.   
    * Output should be a single token - either "information-seeking" or "other"    
  * Wikipedia-Covered vs Not-in-Wikipedia 
    * Wikipedia-Covered are about topics that are prevalent in English Wikipedia mostly mirroring a typical encylopedia. For example: 
      * General Overviews: providing a "quick skim" of a subject to understand the "who, what, when, where, and why".
      * Historical & Biographical Data: Verifying well-documented dates, years in office, and established historical events.
      * Scientific & Formal Concepts: Basic understanding of nature, science, mathematics (e.g., algebra, calculus), and information theory.
      * Common Knowledge: Information that is universally accepted or easily verified by non-specialized maps or public observation.
    * Not-in-Wikipedia are about topics such as current weather, breaking news, non-notable or very niche topics, academic specialized detail, opinions / controversial or under-represented subjects, e-commerce, video / audio streaming, etc.
    * These are mutually exclusive. Provide most confident category. 
    * Output should be a single token - either "wiki" or "non-wiki"  