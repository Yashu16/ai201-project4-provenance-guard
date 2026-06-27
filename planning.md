
### Path taken
Flow 1: Submission Flow

user text 
-> Rate limiter checks if too many requests are being sent -> if yes, send error to user -> if no, API takes the text.
API -> (2 Detection signals) send text to both Groq, and a python script - LLM understands the semantics of the text whereas python script takes sentence length variance, vocabulary diversity into account.  
-> Both of them will give their scores, and we will weigh them to get one final score.
-> This confidence score decides what label to assign to the text out of "High confidence AI, High confidence Human or uncertain" (Transparency label)
-> save this to audit log
-> Return API response

Flow 2: Appeal Flow
Once user sees the label, they are either satisfied or makes an appeal to revert the decision made by the model. 
-> They make an appeal -> goes through rate limiter check, and if it's normal, proceeds to check the submission id and the reason the user put out. 
-> Once the payload validation is done, the code will check the database for the same submission id, and will log this justification reason alongside initial classification while changing the status to "under review"
-> API will proceed to tell the user that their request is under review. 

### Detection Signals
Signal 1(Semantic): Text is sent to Groq(LLM) to understand the semantics of the given text. It looks for the overall flow of the content, phrasing patterns and Cliché AI tropes. AI written text usually has this repeating pattern of, "not this - but this" which humans rarely use in their creative process. 
Blind spot for Signal 1 - LLM might not be able to detect AI writing when content was cleverly prompted by a user to avoid making it look like AI. Along with this, technical or academic content tend to be structured with high vocabulary usage. 

Signal 2(Stylometric): Text is also sent to a python script, which will look at the sentence length variance, punctuation patterns and vocabulary diversity. What makes AI different from human is that, AI uses a lot of punctuation with very uniform sentences. Humans, on the other hand, writes it chaotic, with varied sentence structures. 
Blind spot for signal 2 - Any kind of short text, or content with chaotic structures written purposefully to avoid looking like AI. 

**False Positive scenario**
System would classify the text as "high-confidence AI" when it is not. This will be shown to the user. Once user gets this information, they will appeal through POST api, and appeak process will take place that I have descirbed above. 

### API Surface sketch

1. Content Submission
* **Endpoint:** `POST /api/submit`
* **Rate Limit:** 5 requests per minute 
* **Request Payload (JSON):**
  ```json
  {
    "content": "The raw text string of the poem, story, or article goes here..."
  }

* Response (JSON - 200 OK):

 ```JSON
    {
    "submission_id": "unique-uuid-string",
    "ai_likelihood_score": 0.15,
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
  "reason": "I wrote this myself on a typewriter last Tuesday."
}
Response (JSON - 200 OK):

JSON
{
  "status": "success",
  "message": "Appeal successfully logged. Content status updated to under review.",
  "submission_id": "unique-uuid-string"
}
```

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