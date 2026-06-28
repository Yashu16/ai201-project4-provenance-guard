
### Path taken
**Flow 1: Submission Flow**

User text 
-> Rate limiter checks if too many requests are being sent -> if yes, send error to user -> if no, API takes the text.
API -> (2 Detection signals) send text to both Groq, and a python script - LLM understands the semantics of the text whereas python script takes sentence length variance, vocabulary diversity into account.  
-> Both of them will give their scores, and we will weigh them to get one final score.
-> This confidence score decides what label to assign to the text out of "High confidence AI, High confidence Human or uncertain" (Transparency label)
-> save this to audit log
-> Return API response

**Flow 2: Appeal Flow**

Once user sees the label, they are either satisfied or makes an appeal to revert the decision made by the model. 
-> They make an appeal -> goes through rate limiter check, and if it's normal, proceeds to check the submission id and the reason the user put out. 
-> Once the payload validation is done, the code will check the database for the same submission id, and will log this justification reason alongside initial classification while changing the status to "under review"
-> API will proceed to tell the user that their request is under review. 

### Detection Signals

**Signal 1(Semantic)** 
Text is sent to Groq(LLM) to understand the semantics of the given text. It looks for the overall flow of the content, phrasing patterns and Cliché AI tropes. AI written text usually has this repeating pattern of, "not this - but this" which humans rarely use in their creative process. 

**Blind spot for Signal 1** 
LLM might not be able to detect AI writing when content was cleverly prompted by a user to avoid making it look like AI. Along with this, technical or academic content tend to be structured with high vocabulary usage. 

**Signal 2(Stylometric)** 
Text is also sent to a python script, which will look at the sentence length variance, punctuation patterns and vocabulary diversity. What makes AI different from human is that, AI uses a lot of punctuation with very uniform sentences. Humans, on the other hand, writes it chaotic, with varied sentence structures. 

**Blind spot for signal 2**
Any kind of short text, or content with chaotic structures written purposefully to avoid looking like AI. 

**False Positive scenario**
System would classify the text as "high-confidence AI" when it is not. This will be shown to the user. Once user gets this information, they will appeal through POST api, and appeak process will take place that I have descirbed above. 

**Signals output** 
Each signal would output a score between 0-1, with 1 saying it is highly likely the given text is AI-written and 0 being not AI written (meaning, human written)

Once we have two different scores from two signals, we will use *weighted average* to combine these, with giving more emphasis for stylometric signal (like a 40 (groq)-60 (stylistic) weight because LLM might hallucinate.)

### Structure
**Uncertainty representation**
To make sure False positives are handled carefully, we will divide our threshold into 3 parts. When the two signals output two different scores, we take a weighted average of them, which gives us one score that sits in between 0-1. 
So, anywhere from [0-0.35] is *High-confidence Human*. [0.36-0.74] is *Uncertain*. [0.75-1.00] is *High-Confidence AI*.

**Transparency label design**
*High-confidence Human[0-0.35]:* 
"Verified Human Creator: Our automated system has analyzed the content's structure, semantics and stylistics pattern and are highly confident that this was written entirely by a human. 
*Uncertain[0.36-0.74]:*
"Uncertain attribution: Our automated system has analyzed given text but is unable to confidently say that this is human-written due to mixed signals. We are improving our systems in this regard, thank you for your patience!
*High-Confidence AI[0.75-1.00]:*
"AI-generated Content: This uploaded text was analyzed by our system and we have detected AI written structure and semantics. If you are the creator and believe this classification is a mistake, you can submit your appeal and it will be reviewed by our moderators."

**Appeal workflow**
1. Only the Original creator can submit an Appeal. The request must reference a submission_id. 
2. Information they provide - 
- submission_id: A unique identifier(UUID) linking their appeal directly to the original automated classification record. 
- reason: A plain text justification where user explains why the automated system is wrong with their post. 
3. When appeal is received - First, system validates whether the submission_id exists in our audit log and the reason field isn't empty, and once it confirms that, it fetches that id in our SQLdatabase, and flips the status of that post from "classified" to "under review". And then, it appends the creator's reason text along with a timestamp of when they have made an appeal. 
4. The human reviewer will see status column showing "under review" displaying submission_id, original post, system verdict, signal breakdown, creator's reason and timestamp. 

**Edge cases**
1. A minimalistic short story, written with short, punchy, and heavy repitition of common words will be flagged as AI due to similar sentence structure. The python script will decide it to not have any sentence variation, and marking it as AI. 
2. Most technical/documentation blog posts follow a rigid structure, and going by pure math, this will be flagged as AI too. Especailly LLMs are already trained on such posts, so their output will be similar to those of highly technical posts, which LLM thinks of as AI. 
3. If a non-english speaker were to convert a poem written in their mother tongue, they will use formal words and make sentences very rigid, which will make it seem like its AI. 


### API Surface sketch

1. Content Submission
* **Endpoint:** `POST /api/submit`
* **Rate Limit:** 5 requests per minute 
* **Request Payload (JSON):**
  ```json
  {
    "text": "The raw text string of the poem, story, or article goes here...",
    "creator_id" : "test-user-1"
  }

* Response (JSON - 200 OK):

 ```JSON
    {
    "submission_id": "unique-uuid-string",
    "confidence": 0.15,
    "verdict": "high_confidence_human",
    "transparency_label": "Verified Human Work: Our system is highly confident this content was authored by a human creator."
    }
```

2. Creator appeal
* Endpoint: POST /api/appeal
* Rate Limit: 3 requests per minute
Request Payload (JSON):

```JSON
{
  "submission_id": "unique-uuid-string",
  "creator_id" : "test-user-1",
  "reason": "I wrote this myself on a typewriter last Tuesday."
}
```
Response (JSON - 200 OK):

```JSON
{
  "status": "success",
  "message": "Appeal successfully logged. Content status updated to under review.",
  "submission_id": "unique-uuid-string"
}
```

```markdown
## System Architecture Diagram

### Flow 1: Content Submission Pipeline
[ Incoming Request ]
        │
        ▼
┌────────────────────────────────┐
│ 1. Rate Limiter (Bouncer)      │ ---> (Over Limit: 429 Too Many Requests)
└────────────────────────────────┘
        │ (Allowed)
        ▼
┌────────────────────────────────┐
│ 2. Flask Submission Endpoint   │
└────────────────────────────────┘
        │
        ├──────────────────────────────────────┐
        ▼ (Raw Text)                           ▼ (Raw Text)
┌────────────────────────────────┐     ┌────────────────────────────────┐
│ 3A. Signal 1: Groq LLM API     │     │ 3B. Signal 2: Stylometrics     │
│     (Returns Semantic Score)   │     │     (Returns Structural Score) │
└────────────────────────────────┘     └────────────────────────────────┘
        │ (Score 0.0 - 1.0)                    │ (Score 0.0 - 1.0)
        └───────────────────┬──────────────────┘
                            ▼
               ┌──────────────────────────┐
               │ 4. Score Merger & Math   │ (Weighted Average)
               └──────────────────────────┘
                            │ (Final Combined Score)
                            ▼
               ┌──────────────────────────┐
               │ 5. UX Label Map (Opt. 1) │ (Maps Score to 1 of 3 Labels)
               └──────────────────────────┘
                            │
                            ▼
               ┌──────────────────────────┐
               │ 6. SQLite / JSON Audit   │ (Saves Text, Scores, Verdict)
               └──────────────────────────┘
                            │
                            ▼
               [ JSON API Response Out ]


### Flow 2: Appeal Workflow
[ Incoming Request ]
        │ (submission_id + reason)
        ▼
┌────────────────────────────────┐
│ 1. Rate Limiter & Validation   │ ---> (Missing/Bad Data: 400 Bad Request)
└────────────────────────────────┘
        │ (Validated Payload)
        ▼
┌────────────────────────────────┐
│ 2. Database Record Lookup      │ ---> (ID Not Found: 404 Not Found)
└────────────────────────────────┘
        │ (Record Found)
        ▼
┌────────────────────────────────┐
│ 3. State Update & Append       │ (Flips status to "under review")
│    (Audit Log Database)        │ (Saves creator's justification)
└────────────────────────────────┘
        │
        ▼
   [ JSON API Success Response ]

User sends in a request of their post. Before it gets sent to LLM or the system, the rate limiter will catch if there are too many messages within certain time period from the same IP address.
If not, that post gets sent to both LLM and a python script, each signal giving their score between 0-1. A weighted average takes place between them to give out a final confidence score, which the system uses to give a verdict to the user amongst the written labels. Then, it will save these logs in the database for future reference. 
Once the user sees the label, and if they think the system has incorrectly marked their post as AI generated, they will make their appeal with giving out a reason along with their submission_id. We once again check for rate limit, and if all's good, our system checks for the exact submission_id and if it's present, it updates the status of that post while also appending this reason with timestamp. We give out a user message saying appeal was successful. 

## AI tool plan
Milestone 3: I will give my architecture diagram and detection signals from this file to AI, and ask it to generate code for first signal and a flask app skeleton. To verify my output, I will manually check by giving it few inputs. 

Milestone 4: Again, I provide my architecture diagram and detection signals section from this file to AI, and ask it to generate second signal function along with score combining logic. I will give test it on different inputs with human written and AI generated ones, and see how it outputs the labels. I will check if the score is changing accurately depending on the input, and how consistent my system is. 

Milestone 5: My label variants + Architecture diagram + appeals workflow will be given here to finally build label generation logic and appeal endpoint. To test this, I will manually input a text, see if the labels are showing to the user. And check if the appeal function is working properly by looking at the database after I click on appeal. 