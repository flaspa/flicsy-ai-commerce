# Flicsy — Project Overview

## 1. Concept

**Flicsy is the AI personal-styling spin-off of Mira Picks.**

Mira Picks began as an AI-native fashion magazine: Miranda assigns, Andy reads the fashion press, Emily reads social culture, Nigel assesses, and Miranda decides.

Flicsy takes that same editorial intelligence and turns it toward an individual shopper.

Instead of asking:

> What fashion story is worth publishing?

Flicsy asks:

> **What should this person buy?**

The customer describes an occasion, preferences, constraints, and optionally shares a recent photo. Miranda asks a small number of clarifying questions, then sends the brief to the fashion desk. The agents research fashion context, social signals, real purchasable products, and the coherence of complete looks before Miranda presents the final recommendations.

The goal for the hackathon is a complete commerce journey:

**customer intent → agent collaboration → real products → complete outfits → cart → Stripe test checkout**

---

## 2. Customer Experience

A customer begins conversationally rather than filling out a long form.

Example:

> “I’m going to a gala dinner in San Francisco next month. Here’s a recent photo of me. I love skiing, I wear a lot of blue, and I’d like something elegant but not conventional.”

The photo can provide visible styling context such as proportions, existing clothing, colors, and overall styling. The customer can also explicitly provide:

- budget
- size and fit preferences
- preferred or disliked brands
- shoe preferences
- colors
- dress code
- pieces they already own
- things they do not want to wear

Miranda asks only the questions that materially affect the recommendation, for example:

- “Black tie or cocktail?”
- “What’s your budget?”
- “Dress, suit, or open to either?”
- “Are heels okay?”
- “Anything you definitely don’t want to wear?”

Once the brief is clear, Miranda tells the customer:

> **“Let me consult the fashion desk.”**

The rest of the team then works behind the scenes.

---

## 3. The Flicsy Fashion Desk

The hackathon version extends the Mira Picks fashion desk with Serena as the fifth character. Miranda, Andy, Emily, and Nigel carry over from Mira Picks; Serena is new in Flicsy and follows the same visual language.

### Miranda — Lead Stylist

**Question:** What does this client actually need?

Responsibilities:

- talks directly to the customer
- asks clarifying questions
- converts the conversation into a structured styling brief
- delegates research to the fashion desk
- receives Nigel’s critique and Serena’s product selections
- makes the final styling decision
- presents the final 1–3 looks to the customer

Miranda approves **once, at the end**.

She is the only agent that makes the final decision.

---

### Andy — Fashion Editor

**Question:** What does the fashion establishment suggest?

Primary tool: **Tavily**

Responsibilities:

- searches fashion magazines
- reviews runway and editorial coverage
- searches designer and fashion-industry sources
- identifies silhouettes, styling directions, materials, colors, and relevant editorial context
- reports evidence and sources rather than choosing products

Andy’s output is fashion direction relevant to the client’s brief.

Example:

> “Current eveningwear coverage is leaning toward sculptural tailoring, deep saturated blues, and less conventional formal footwear.”

---

### Emily — Social & Culture Editor

**Question:** What are people actually wearing and talking about?

Primary data source: **Bright Data**, using the existing fashion/TikTok collection pattern from Mira Picks

Responsibilities:

- searches or retrieves social fashion signals
- uses the existing Bright Data fashion trend data where useful
- surfaces social styling patterns, emerging aesthetics, and cultural context
- distinguishes observed signals from interpretation
- does not choose products

Emily’s output is current social/cultural evidence relevant to the styling brief.

Example:

> “Socially, formal tailoring is frequently being styled with flats, minimal jewelry, and saturated blue accents rather than traditional evening accessories.”

---

### Serena — Personal Shopper

**Question:** What can the client actually buy?

Primary tool: **Moss**

Responsibilities:

- searches the indexed product catalog
- searches indexed retailer catalogs, starting with Everlane; additional retailers can be added
- uses Miranda’s brief plus Andy and Emily’s findings
- returns product name, retailer, price, image, URL, size/availability when available
- assembles 2–3 complete outfit candidates
- revises products when Nigel rejects or questions part of a look
- builds the proposed shopping bag

Moss is **Serena’s searchable product catalog**, not another agent.

Example output:

> **Serena’s Shopping Bag**  
> Zara — blue satin dress — $129  
> Nordstrom — silver slingbacks — $145  
> Everlane — cashmere wrap — $168  
> **Total: $442**

---

### Nigel — Fashion Director / Critic

**Question:** Does this actually work as a look for this client?

Responsibilities:

- receives Miranda’s brief
- receives Andy’s editorial evidence
- receives Emily’s social/cultural evidence
- reviews Serena’s proposed outfits
- critiques fit, coherence, occasion, budget, styling, and evidence quality
- can reject an outfit or request substitutions
- cannot make the final customer-facing decision

Nigel is deliberately opinionated and discerning.

Example:

> “Look 2 works. Look 1 is competent but forgettable. Replace the shoes. Look 3 exceeds the client’s stated budget once accessories are included.”

---

## 4. End-to-End Agent Workflow

```text
CUSTOMER
   |
   v
MIRANDA
Clarifies intent and creates styling brief
   |
   v
BAND ROOM
   |
   +--------------------+
   |                    |
   v                    v
ANDY                  EMILY
Tavily                Bright Data
Fashion press         Social/culture
   |                    |
   +---------+----------+
             |
             v
          SERENA
           Moss
  Real purchasable products
  + complete outfit candidates
             |
             v
           NIGEL
   Critiques complete looks
             |
        revisions if needed
             |
             v
          MIRANDA
       Final selection
             |
             v
       CUSTOMER LOOKS
             |
             v
      ADD LOOK TO CART
             |
             v
   STRIPE TEST CHECKOUT
```

The visible handoff flow is:

**Miranda → @Andy + @Emily → @Serena → @Nigel → @Miranda**

---

## 5. How the Sponsor Stack Fits

### ZooWork — where the agents live

**Target runtime architecture.** Miranda, Andy, Emily, Serena, and Nigel are designed to run as ZooWork managed agents. This section describes the target until the five ZooWork agents are actually instantiated.

ZooWork provides:

- managed agent runtime
- agent configuration
- sessions
- event streams
- models
- tools / MCP access
- isolated execution

ZooWork is the target runtime layer for the fashion desk.

---

### Band — how the agents coordinate

**Target runtime architecture.** This section describes the target until the Band handoffs between the five agents are actually instantiated.

Band is the backstage room where the agents communicate.

It should be essential to the workflow rather than decorative.

A styling request becomes a Band room. Agents act through explicit handoffs and `@mentions`.

Example:

```text
Miranda → @Andy
Find a fashion direction for a formal gala that does not feel conservative.

Miranda → @Emily
What are we seeing in evening dressing socially right now?

Andy
Editorial direction: sculptural tailoring and saturated blues.

Emily → @Serena
Cobalt accessories and formal flats are showing strongly in the social evidence.

Serena → @Nigel
I have three complete looks under $800.

Nigel → @Serena
Look 2 works. Replace the shoes on Look 1.

Serena
Revised Look 1 ready.

Nigel → @Miranda
Looks 1 and 2 are coherent with the brief. Look 3 exceeds budget.

Miranda
Approved. Present 1 and 2, plus one alternative direction.
```

If Band is removed, the handoffs, shared conversation, and coordination record break.

---

### Moss — Serena’s product memory and retrieval

Moss indexes real merchant/product data.

Initial merchant data can come from crawlable retailer URLs such as Everlane and later other retailers.

Flow:

```text
Retailer URLs
   ↓
Moss index
   ↓
Serena semantic search
   ↓
Real product candidates
   ↓
Nigel critique
   ↓
Miranda approval
   ↓
Cart
```

Moss should be used for fast semantic retrieval such as:

> “Elegant but unconventional gala look, strong blue affinity, no stilettos, under $800.”

---

### Tavily — Andy’s fashion research tool

Tavily is used for open-web editorial research:

- fashion magazines
- runway coverage
- designer/editorial sites
- current fashion context
- comparisons and reviews when relevant

Andy uses Tavily to bring fashion-establishment context into the styling process.

---

### Bright Data — Emily’s social/cultural evidence

Bright Data provides the social-data acquisition layer.

For the hackathon, the existing Mira Picks TikTok fashion dataset and collection pattern can be reused conceptually:

```text
fashion query
   ↓
Bright Data
   ↓
normalized social evidence
   ↓
Emily
```

The existing data can reduce latency during the live demo.

---

### Stripe — transaction completion

Stripe runs in **test mode**.

The final page can include:

- Add Look to Cart
- cart total
- checkout
- Stripe test payment
- confirmation screen

This demonstrates a complete commerce flow without claiming that the third-party retailer received a real order.

---

### Entire — development provenance

Entire is used to capture the development process itself.

The repository was configured for Entire before the application build. Entire captures Claude Code sessions, prompts, tool calls, checkpoints, and commit context.

Hackathon proof can show:

```text
Claude session
   ↓
real project change
   ↓
local Git commit
   ↓
Entire checkpoint
   ↓
prompt / tool / session provenance attached to the change
```

Entire is not part of Flicsy’s runtime. It documents how Flicsy was built.

---

## 6. User Interface

The product should preserve the visual storytelling that worked well in Mira Picks while separating the polished customer experience from the engineering/backstage view.

### A. Mira Picks landing page

Re-create only enough of the original magazine to establish the origin story.

Message:

> **Mira Picks launches Flicsy.**  
> Fashion intelligence, now personal.

Include a prominent CTA:

> **Meet Flicsy — Your Personal Fashion Desk**

This page can be mostly static and should reuse the Mira Picks visual language where practical.

---

### B. Your Stylist

Customer-facing conversation with Miranda.

Capabilities:

- natural-language request
- optional photo upload
- preferences
- budget
- size/fit information
- Miranda’s clarification questions

When the brief is complete:

> **“Let me consult the fashion desk.”**

---

### C. The Fashion Desk

Adapt the existing Mira Picks horizontal agent workflow.

```text
Miranda → Andy → Emily → Serena → Nigel → Miranda
```

Each card shows:

- portrait
- name
- role
- the question the agent answers
- current state
- live status line

Possible states:

- queued
- working
- done
- skipped
- blocked

Example status lines:

- Andy: “Reading fashion press…”
- Emily: “Reading social culture…”
- Serena: “Searching the Moss catalog…”
- Nigel: “Reviewing three looks…”
- Miranda: “Making the final selection…”

Expandable evidence sections:

- **Andy’s Press Desk**
- **Emily’s Clipping Book**
- **Serena’s Shopping Bag**
- **Nigel’s Notes**

---

### D. Behind the Curtain

This tab shows the actual Band room.

It should expose:

- agent messages
- `@mentions`
- handoffs
- timestamps
- tool activity where useful
- blocking/revision requests
- final approval

This view proves that the visible agent workflow is real coordination rather than UI theater.

---

### E. Miranda’s Edit / Your Looks

The final customer-facing page should be polished and visually distinct from the backstage console.

Hero:

> **For your gala, Miranda selected these looks.**

Each look should show:

- complete outfit
- real product images
- retailer
- product name
- price
- size / availability when available
- product URL
- total outfit price
- short explanation from Miranda

Actions:

- **Add Look to Cart**
- edit / replace an item
- ask Miranda for another direction
- checkout

The relationship should remain conversational rather than ending after one recommendation.

---

## 7. Demo Scenario

Primary demo:

> “I’m going to a gala dinner in San Francisco next month. Here’s a recent photo of me. I love skiing, I wear a lot of blue, and I’d like something elegant but not conventional.”

Miranda clarifies:

- dress code
- budget
- dress vs. tailoring
- footwear constraints
- dislikes

Then:

1. Miranda creates the styling brief.
2. Andy researches editorial fashion context.
3. Emily contributes social/cultural signals.
4. Serena searches Moss for real products and assembles outfit candidates.
5. Nigel critiques the looks and requests substitutions if needed.
6. Miranda chooses the final looks.
7. The customer sees 1–3 complete purchasable outfits.
8. The customer adds a look to the cart.
9. Stripe test checkout completes the demo.

---

## 8. Product Story

The concise pitch is:

> **Mira Picks was an AI-native fashion magazine. Flicsy is the business its editorial team launches next: a personal styling service where the same AI fashion desk doesn’t just tell you what’s fashionable — it shops for you.**

The commerce objective is **revenue / conversion**: move a shopper from ambiguous intent to a complete, purchasable look.

Flicsy is not a generic shopping chatbot. It is a visible team of specialized fashion agents that combines editorial intelligence, social context, product retrieval, critique, and a real commerce endpoint.

---

## 9. Build Priorities for the Hackathon

The priority is one convincing end-to-end workflow, not broad feature coverage.

### Must work

1. Miranda customer conversation and styling brief
2. visible five-agent Fashion Desk
3. Band-based agent handoffs
4. ZooWork-hosted agents
5. Andy / Tavily research
6. Emily / Bright Data social evidence
7. Serena / Moss product retrieval
8. Nigel critique
9. Miranda final looks
10. real product cards
11. Add Look to Cart
12. Stripe test checkout

### Nice to have

- photo-informed styling context
- multiple merchant catalogs
- persistent customer preferences
- item replacement/refinement
- richer live Band visualization
- magazine landing page with several editorial stories

### Defer

- real third-party retailer checkout
- inventory management
- autonomous purchasing without human approval
- large-scale catalog ingestion
- production rights/branding cleanup for the movie-inspired hackathon characters.
