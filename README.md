# ai201-project4-provenance-guard

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


### Detection Signals

**Signal 1(Semantic)** 
Text is sent to Groq(LLM) to understand the semantics of the given text. It looks for the overall flow of the content, phrasing patterns and Cliché AI tropes. AI written text usually has this repeating pattern of, "not this - but this" which humans rarely use in their creative process. 

**Blind spot for Signal 1** 
LLM might not be able to detect AI writing when content was cleverly prompted by a user to avoid making it look like AI. Along with this, technical or academic content tend to be structured with high vocabulary usage. 

**Signal 2(Stylometric)** 
Text is also sent to a python script, which will look at the sentence length variance, punctuation patterns and vocabulary diversity. What makes AI different from human is that, AI uses a lot of punctuation with very uniform sentences. Humans, on the other hand, writes it chaotic, with varied sentence structures. 

**Blind spot for signal 2**
Any kind of short text, or content with chaotic structures written purposefully to avoid looking like AI. 

I chose these two signals because they complement each other by identifying different context of the text as described within each signal. I get semantics from LLM (signal 1) and identify sentence length from signal 2 (python code). 

### Confidence Scoring 
Each signal would output a score between 0-1, with 1 saying it is highly likely the given text is AI-written and 0 being not AI written (meaning, human written)

Once we have two different scores from two signals, I have used *weighted average* to combine these, with giving more emphasis for stylometric signal (40 for (groq) and 60 for(stylistic) weight because LLM might hallucinate.)

Score validation was done in different ways:
1. Standalone signal testing (compare_signals.py)
We ran both signals independently on the same 4 inputs before wiring them into the app, and compared where they agreed vs diverged. This told us Signal 1 was the stronger discriminator and Signal 2 needed recalibration.

2. Iterative calibration of Signal 2
Signal 2's first version scored everything in a narrow 0.33–0.54 band — not enough separation. We identified the root cause (uniformity threshold too loose, phrase detection underweighted) and recalibrated until the clearly AI text scored 0.609 vs the human text at 0.056 — a clear gap.

3. End-to-end submission testing
We submitted all 4 sample texts through the full API and checked that the combined weighted score produced sensible verdicts:

Clearly AI → high_confidence_ai
Clearly human → high_confidence_human
Formal human writing → uncertain (correct — it's genuinely ambiguous)
Lightly edited AI → high_confidence_human (acknowledged as a known false negative / blind spot)
4. Threshold adjustment
We lowered the AI threshold from 0.75 to 0.65 based on observed score ranges, and documented the reason in planning.md.


Examples:

(.venv) PS P:\AI201\week-4\ai201-project4-provenance-guard> # High confidence AI

>> Invoke-RestMethod -Uri http://localhost:5000/api/submit -Method POST -ContentType "application/json" -Body '{"creator_id": "test-user-1", "text": "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment."}' | Format-List
>> 
>> <> High confidence Human
>> Invoke-RestMethod -Uri http://localhost:5000/api/submit -Method POST -ContentType "application/json" -Body '{"creator_id": "test-user-1", "text": "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better. probably wont go back unless someone drags me there"}' | Format-List
>> 

attribution   : high_confidence_ai
confidence    : 0.7052
label         : AI-generated Content: This uploaded text was analyzed by our system and we have detected AI written structure and semantics. If you are the creator and believe this classification is a mistake, you can submit your appeal and it will be reviewed by our moderators.
submission_id : 33b8d1d6-f482-49de-9635-df1add78bd0f

It's audit log:
  {
    "submission_id": "33b8d1d6-f482-49de-9635-df1add78bd0f",
    "creator_id": "test-user-1",
    "timestamp": "2026-06-28T23:23:57.891Z",
    "attribution": "high_confidence_ai",
    "confidence": 0.7052,
    "llm_score": 0.85,
    "stylometric_score": 0.6087,
    "status": "classified"
  }

attribution   : high_confidence_human
confidence    : 0.0815
label         : Verified Human Creator: Our automated system has analyzed the content's structure, semantics and stylistics pattern and are highly confident that this was written entirely by a human.
submission_id : 5ff08e18-5de1-4df4-ba07-420329eca549

It's audit log:
{
    "submission_id": "5ff08e18-5de1-4df4-ba07-420329eca549",
    "creator_id": "test-user-1",
    "timestamp": "2026-06-28T23:23:58.219Z",
    "attribution": "high_confidence_human",
    "confidence": 0.0815,
    "llm_score": 0.12,
    "stylometric_score": 0.0559,
    "status": "classified"
  }

(.venv) PS P:\AI201\week-4\ai201-project4-provenance-guard> Invoke-RestMethod -Uri http://localhost:5000/api/submit -Method POST -ContentType "application/json" -Body '{"creator_id": "test-user-1", "text": "The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and the unintended consequences of prolonged low interest rates on equity and real estate valuations."}' | Format-List
>> 
attribution   : uncertain
confidence    : 0.3896
label         : Uncertain Attribution: Our automated system has analyzed given text but is unable to 
                confidently say that this is human-written due to mixed signals. We are improving 
                our systems in this regard, thank you for your patience!
submission_id : 09387c9a-55c1-45bc-b641-254d1c2382b4

It's audit log:
 {
    "submission_id": "09387c9a-55c1-45bc-b641-254d1c2382b4",
    "creator_id": "test-user-1",
    "timestamp": "2026-06-28T23:28:56.269Z",
    "attribution": "uncertain",
    "confidence": 0.3896,
    "llm_score": 0.81,
    "stylometric_score": 0.1094,
    "status": "classified"
  }

**Transparency label design**
*High-confidence Human[0-0.35]:* 
"Verified Human Creator: Our automated system has analyzed the content's structure, semantics and stylistics pattern and are highly confident that this was written entirely by a human. 
*Uncertain[0.36-0.64]:*
"Uncertain attribution: Our automated system has analyzed given text but is unable to confidently say that this is human-written due to mixed signals. We are improving our systems in this regard, thank you for your patience!
*High-Confidence AI[0.65-1.00]:*
"AI-generated Content: This uploaded text was analyzed by our system and we have detected AI written structure and semantics. If you are the creator and believe this classification is a mistake, you can submit your appeal and it will be reviewed by our moderators."

**Rate Limiting**
Submit endpoint (POST /api/submit): 5 per minute, 50 per day

Reasoning: A legitimate creator submitting their own work rarely needs more than 5 submissions per minute — that's already one every 12 seconds. The daily cap of 50 reflects a realistic upper bound for a single writer's session. Together these block scripted flooding (which would hit the per-minute wall immediately) while not inconveniencing genuine users.

Appeal endpoint (POST /api/appeal): 3 per minute

Reasoning: Appeals are a deliberate, manual action — a user reading a verdict and writing a justification takes time. 3 per minute is more than enough for human behavior but stops anyone from scripting bulk appeals against multiple submission IDs.

Example below showing rate limiting working: 

(.venv) PS P:\AI201\week-4\ai201-project4-provenance-guard> 1..7 | ForEach-Object {
>>     try {
>>         $response = Invoke-WebRequest -Uri http://localhost:5000/api/submit -Method POST -ContentType "application/json" -Body '{"text": "This is a test submission for rate limit testing purposes only.", "creator_id": "ratelimit-test"}'
>>         Write-Output $response.StatusCode
>>     } catch {
>>         Write-Output $_.Exception.Response.StatusCode.value__
>>     }
>> }
>> 
                                                                                                      
Security Warning: Script Execution Risk                                                               
Invoke-WebRequest parses the content of the web page. Script code in the web page might be run when   
the page is parsed.                                                                                   
      RECOMMENDED ACTION:
      Use the -UseBasicParsing switch to avoid script code execution.

      Do you want to continue?
    
[Y] Yes  [A] Yes to All  [N] No  [L] No to All  [S] Suspend  [?] Help (default is "N"): a
200
200
200
200
200
429
429

**Known Limitations**
1. Lightly edited AI output → misclassified as human
Sample 4 (the remote work paragraph) scored 0.179 — high_confidence_human — despite being AI-generated text with minor human edits. 
Both signals got fooled: Signal 1 because the casual tone ("I've been thinking", "genuine tradeoffs") masked the AI origin, and Signal 2 because there were no formal AI phrases and the sentence lengths varied enough. This is the hardest case for any detection system. 
2. Formal human writing → misclassified as uncertain
Sample 3 (the monetary policy paragraph) scored 0.544 — uncertain — despite being human-written academic prose. Signal 1 flagged it at 0.81 because LLMs are trained on exactly this kind of text and the phrasing looks AI-like. Since LLM scored so high, it pulled the total score towards it being "AI-generated" 

## Spec Reflection

**one way the spec helped me**: By writing down the whole architecture before touching the code, I was able to get an understanding of how the text would flow through my system and that has helped me get a good grasp of what I was doing next.

**One way my implementation changed from spec**: My initial plan was to split the three labels as 0-0.35, 0.36-0.74, 0.75-1.00 for "human written, uncertain and AI written" respectively. However, after testing out different strategies with my signals, I found out that 0.75 might be extremely high of a number especially when I am taking weighted average of two signals. So, I brought it down to 0.65. And changed the range of uncertain as required. 

## AI usage reflection

**Instance 1:** I have asked AI to implement my signal function based on my planning.md file, and once it did, I found the ranges of each label to not work as intended. So, I changed 0.75 to 0.65 as I have explained above. I have changed both code and spec implementation. 

**Instance 2:** I have asked AI to brainstorm different methods to combine both signals, and out of differnt options it suggested - like, choosing by vote of each signal, giving maximum importance to stylometric signal, I have chosen to do weighted average and give 40% to groq and 60% to stylometric signal. 

appeal command
Invoke-RestMethod -Uri http://localhost:5000/api/appeal -Method POST -ContentType "application/json" -Body '{"submission_id": "2067a907-343e-4bdf-8108-460dd642136e", "creator_id": "test-user-1", "creator_reasoning": "I wrote this myself, the system incorrectly flagged my work."}' | Format-List

rate limit command
1..7 | ForEach-Object {
    try {
        $response = Invoke-WebRequest -Uri http://localhost:5000/api/submit -Method POST -ContentType "application/json" -Body '{"text": "This is a test submission for rate limit testing purposes only.", "creator_id": "ratelimit-test"}'
        Write-Output $response.StatusCode
    } catch {
        Write-Output $_.Exception.Response.StatusCode.value__
    }
}
