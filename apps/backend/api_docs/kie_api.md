# Getting Started with KIE API (Important)

> Welcome to **KIE**. This guide walks you through the essential information you need to start integrating KIE APIs into your product, including models, pricing, authentication, request flow, limits, and support.

We aim to be transparent, practical, and developer-friendly. Please read this carefully before going to production.

## 1. Available Models & Playground

You can find the **latest supported models** on our Market page:

👉 [https://kie.ai/market](https://kie.ai/market)

* We continuously update and onboard new models as soon as they are stable.
* Each model page links to its **Playground**, where you can test and experiment directly in our UI before calling the API.
* The Playground is the best place to understand model behavior, parameters, and output formats.

***

## 2. Pricing

The complete and up-to-date pricing list is available here:

👉 [https://kie.ai/pricing](https://kie.ai/pricing)

* Our prices are typically **30%–50% lower than official APIs**.
* For some models, discounts can reach **up to 80%**.
* Pricing may change as upstream providers adjust their costs, so always refer to the pricing page for the latest numbers.

***

## 3. Creating and Securing Your API Key

Create and manage your API keys here:

👉 [https://kie.ai/api-key](https://kie.ai/api-key)

**Important security notes:**

* **Never expose your API key in frontend code** (browser, mobile apps, public repositories).
* Treat your API key as a secret.

To help protect your usage, we provide:

* **Rate limits per key** (hourly, daily, and total usage caps)
* **IP whitelist** support, allowing only approved server IPs to access the API

These features help prevent accidental overuse and unauthorized requests.

***

## 4. Required Request Headers

Every API request **must** include the correct headers:

```http  theme={null}
Authorization: Bearer <YOUR_API_KEY>
Content-Type: application/json
```

If these headers are missing or incorrect, you may receive:

```json  theme={null}
{"code":401,"msg":"You do not have access permissions"}
```

Always double-check your headers when debugging authentication issues.

***

## 5. Logs & Task Details

You can inspect all your historical tasks here:

👉 [https://kie.ai/logs](https://kie.ai/logs)

For each task, you can view:

* Creation time
* Model used
* Input parameters
* Task status
* Credit consumption
* Final results or error details

If you ever suspect incorrect credit usage, this page is the source of truth for verification.

***

## 6. Data Retention Policy

Please note our retention rules:

* **Generated media files**: stored for 14 days, then automatically deleted
* **Log records** (text / metadata): stored for 2 months, then automatically deleted

If you need long-term access, make sure to download and store results on your side in time.

***

## 7. Asynchronous Task Model

All generation tasks on KIE are asynchronous.

A successful request returns:

* **HTTP 200**
* A `task_id`

<Warning>
  A 200 response only means the task was created, not completed.
</Warning>

To get the final result, you must either:

* Provide a callback (webhook) URL in the request, or
* Actively poll the "query record info" API using the `task_id`

***

## 8. Rate Limits & Concurrency

By default, we apply the following limits:

* Up to 20 new generation requests per 10 seconds
* This typically allows 100+ concurrent running tasks
* Limits are applied per account

If you exceed the limit:

* Requests will be rejected with HTTP 429
* Rejected requests will not enter the queue

For most users, this is more than sufficient.
If you consistently hit 429 errors, you may contact support to request a higher limit — approvals are handled cautiously.

***

## 9. Developer Support

The recommended support channels are available directly from the dashboard (bottom-left menu):

* Get help on Discord
* Get help on Telegram

What you get:

* Private, 1-on-1 channels
* Your data and conversations remain confidential
* Faster and more technical responses

**Support hours:**
UTC 21:00 – UTC 17:00 (next day)

You may also email us at [support@kie.ai](mailto:support@kie.ai), but this is not the preferred or fastest option.

***

## 10. Stability Expectations

We provide access to top-tier, highly competitive APIs at very aggressive pricing.

That said:

* We are not perfect
* Our overall stability may be slightly lower than official providers
* This is a conscious trade-off

In practice, KIE is stable enough to support production workloads and long-term business growth, but we believe in setting realistic expectations upfront.

***

## 11. About the Team

KIE is built by a small startup team.

* We move fast
* We care deeply about developer experience
* We are constantly improving

At the same time, we acknowledge that:

* Not everything is perfect
* We can't satisfy every use case immediately

Your feedback helps us improve — and we genuinely appreciate it.


---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://docs.kie.ai/llms.txt

# Get Task Details

> Query the status and results of any task created in the Market models

## Overview

Use this endpoint to query the status and results of any task created through Market model APIs. This is a unified query interface that works with all models under the Market category.

<Info>
  This endpoint works with all Market models including Seedream, Grok Imagine, Kling, Claude, and any future models added to the Market.
</Info>

## API Endpoint

```
GET https://api.kie.ai/api/v1/jobs/recordInfo
```

## Query Parameters

<ParamField query="taskId" type="string" required>
  The unique task identifier returned when you created the task.

  **Example**: `task_12345678`
</ParamField>

## Request Example

<CodeGroup>
  ```bash cURL theme={null}
  curl -X GET "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=task_12345678" \
    -H "Authorization: Bearer YOUR_API_KEY"
  ```

  ```javascript Node.js theme={null}
  const response = await fetch('https://api.kie.ai/api/v1/jobs/recordInfo?taskId=task_12345678', {
    method: 'GET',
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY'
    }
  });

  const result = await response.json();
  console.log('Task Status:', result.data.state);
  console.log('Result:', result.data.resultJson);
  ```

  ```python Python theme={null}
  import requests

  response = requests.get(
      'https://api.kie.ai/api/v1/jobs/recordInfo',
      params={'taskId': 'task_12345678'},
      headers={'Authorization': 'Bearer YOUR_API_KEY'}
  )

  result = response.json()
  print('Task Status:', result['data']['state'])
  print('Result:', result['data']['resultJson'])
  ```
</CodeGroup>

## Response Format

<ResponseExample>
  ```json Success Response theme={null}
  {
    "code": 200,
    "message": "success",
    "data": {
      "taskId": "task_12345678",
      "model": "grok-imagine/text-to-image",
      "state": "success",
      "param": "{\"model\":\"grok-imagine/text-to-image\",\"callBackUrl\":\"https://your-domain.com/api/callback\",\"input\":{\"prompt\":\"Cinematic portrait...\",\"aspect_ratio\":\"3:2\"}}",
      "resultJson": "{\"resultUrls\":[\"https://example.com/generated-content.jpg\"]}",
      "failCode": "",
      "failMsg": "",
      "completeTime": 1698765432000,
      "createTime": 1698765400000,
      "updateTime": 1698765432000
    }
  }
  ```
</ResponseExample>

## Response Fields

<ResponseField name="code" type="integer">
  Response status code. `200` indicates success.
</ResponseField>

<ResponseField name="message" type="string">
  Response message. Typically `"success"` for successful queries.
</ResponseField>

<ResponseField name="data" type="object">
  The task data object containing all task information.

  <Expandable title="data properties">
    <ResponseField name="taskId" type="string">
      The unique identifier for this task.
    </ResponseField>

    <ResponseField name="model" type="string">
      The model used for this task (e.g., `grok-imagine/text-to-image`, `seedream-4.0`, `kling-1.0`).
    </ResponseField>

    <ResponseField name="state" type="string">
      Current state of the task. See [Task States](#task-states) below for details.

      **Possible values**: `waiting`, `queuing`, `generating`, `success`, `fail`
    </ResponseField>

    <ResponseField name="param" type="string">
      JSON string containing the original request parameters used to create the task.
    </ResponseField>

    <ResponseField name="resultJson" type="string">
      JSON string containing the generated content URLs. Only present when `state` is `success`.

      **Example**: `{"resultUrls":["https://example.com/image.jpg"]}`
    </ResponseField>

    <ResponseField name="failCode" type="string">
      Error code if the task failed. Empty string if successful.
    </ResponseField>

    <ResponseField name="failMsg" type="string">
      Error message if the task failed. Empty string if successful.
    </ResponseField>

    <ResponseField name="completeTime" type="integer">
      Unix timestamp (in milliseconds) when the task completed.
    </ResponseField>

    <ResponseField name="createTime" type="integer">
      Unix timestamp (in milliseconds) when the task was created.
    </ResponseField>

    <ResponseField name="updateTime" type="integer">
      Unix timestamp (in milliseconds) when the task was last updated.
    </ResponseField>
  </Expandable>
</ResponseField>

## Task States

| State        | Description                                | Action                                     |
| ------------ | ------------------------------------------ | ------------------------------------------ |
| `waiting`    | Task is queued and waiting to be processed | Continue polling                           |
| `queuing`    | Task is in the processing queue            | Continue polling                           |
| `generating` | Task is currently being processed          | Continue polling                           |
| `success`    | Task completed successfully                | Parse `resultJson` to get results          |
| `fail`       | Task failed                                | Check `failCode` and `failMsg` for details |

## Polling Best Practices

<AccordionGroup>
  <Accordion title="Recommended Polling Intervals">
    * **Initial polls (first 30 seconds)**: Every 2-3 seconds
    * **After 30 seconds**: Every 5-10 seconds
    * **After 2 minutes**: Every 15-30 seconds
    * **Maximum polling duration**: Stop after 10-15 minutes and investigate

    <Tip>
      Use exponential backoff to reduce server load and API costs.
    </Tip>
  </Accordion>

  <Accordion title="Using Callbacks Instead of Polling">
    For production applications, we strongly recommend using the `callBackUrl` parameter when creating tasks:

    * **No polling needed**: Your server receives notifications automatically
    * **Lower API costs**: Eliminates continuous polling requests
    * **Better performance**: Immediate notifications when tasks complete
    * **Reduced latency**: No delay between completion and notification

    See individual model documentation for callback implementation details.
  </Accordion>

  <Accordion title="Handling Completed Tasks">
    When `state` is `success`:

    1. Parse the `resultJson` string to JSON
    2. Extract the `resultUrls` array
    3. Download generated content immediately
    4. Store content in your own storage

    **Important**: Generated content URLs typically expire after 24 hours.
  </Accordion>
</AccordionGroup>

## Error Handling

<ResponseExample>
  ```json Task Failed theme={null}
  {
    "code": 200,
    "message": "success",
    "data": {
      "taskId": "task_12345678",
      "model": "grok-imagine/text-to-image",
      "state": "fail",
      "param": "{\"model\":\"grok-imagine/text-to-image\",\"input\":{\"prompt\":\"...\"}}",
      "resultJson": "",
      "failCode": "422",
      "failMsg": "Invalid prompt: prompt contains prohibited content",
      "completeTime": 1698765432000,
      "createTime": 1698765400000,
      "updateTime": 1698765432000
    }
  }
  ```
</ResponseExample>

### Common Error Codes

| Code  | Description                               | Solution                                   |
| ----- | ----------------------------------------- | ------------------------------------------ |
| `401` | Unauthorized - Invalid or missing API key | Check your API key                         |
| `404` | Task not found                            | Verify the taskId is correct               |
| `422` | Validation error in original request      | Check the `failMsg` for details            |
| `500` | Internal server error                     | Retry after a few minutes                  |
| `501` | Generation failed                         | Check `failMsg` for specific error details |

## Example: Complete Polling Flow

```javascript Node.js theme={null}
async function pollTaskStatus(taskId, maxAttempts = 60, interval = 5000) {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const response = await fetch(
      `https://api.kie.ai/api/v1/jobs/recordInfo?taskId=${taskId}`,
      {
        headers: { 'Authorization': 'Bearer YOUR_API_KEY' }
      }
    );
    
    const result = await response.json();
    const { state, resultJson, failMsg } = result.data;
    
    console.log(`Attempt ${attempt + 1}: State = ${state}`);
    
    if (state === 'success') {
      const results = JSON.parse(resultJson);
      console.log('✅ Task completed!');
      console.log('Results:', results.resultUrls);
      return results;
    }
    
    if (state === 'fail') {
      console.error('❌ Task failed:', failMsg);
      throw new Error(failMsg);
    }
    
    // Still processing, wait before next poll
    await new Promise(resolve => setTimeout(resolve, interval));
  }
  
  throw new Error('Task timed out after maximum attempts');
}

// Usage
try {
  const results = await pollTaskStatus('task_12345678');
  console.log('Generated content URLs:', results.resultUrls);
} catch (error) {
  console.error('Error:', error.message);
}
```

## Rate Limits

* **Maximum query rate**: 10 requests per second per API key
* **Recommended interval**: 2-5 seconds between polls

<Warning>
  Excessive polling may result in rate limiting. Use callbacks for production applications.
</Warning>

## Related Resources

<CardGroup cols={2}>
  <Card title="Market Overview" icon="store" href="/market/quickstart">
    Explore all available models
  </Card>

  <Card title="Get Account Credits" icon="coins" href="/common-api/get-account-credits">
    Check your remaining credits
  </Card>
</CardGroup>


## OpenAPI

````yaml market/common/get-task-detail.json get /api/v1/jobs/recordInfo
openapi: 3.0.0
info:
  title: Kie.ai Common API
  description: Kie.ai Common API Documentation - Task Status Query
  version: 1.0.0
  contact:
    name: Technical Support
    email: support@kie.ai
servers:
  - url: https://api.kie.ai
    description: API Server
security:
  - BearerAuth: []
paths:
  /api/v1/jobs/recordInfo:
    get:
      summary: Get Task Details
      description: >-
        Query the status and results of any task created in the Market models.
        This is a unified query interface that works with all models under the
        Market category.


        ### Supported Models

        This endpoint works with all Market models including:

        - **Seedream**: seedream, seedream-v4-text-to-image, etc.

        - **Grok Imagine**: text-to-image, image-to-video, text-to-video,
        upscale

        - **Kling**: text-to-video, image-to-video models

        - **ElevenLabs**: Audio processing models

        - **Claude**: Language models

        - **And any future models added to the Market**


        ### Task States

        - **waiting**: Task is queued and waiting to be processed

        - **queuing**: Task is in the processing queue

        - **generating**: Task is currently being processed

        - **success**: Task completed successfully

        - **fail**: Task failed


        ### Best Practices

        - **Use callbacks for production**: Include `callBackUrl` when creating
        tasks to avoid polling

        - **Implement exponential backoff**: Start with 2-3 second intervals,
        increase gradually

        - **Handle timeouts**: Stop polling after 10-15 minutes

        - **Download results immediately**: Generated content URLs typically
        expire after 24 hours
      operationId: get-task-details
      parameters:
        - name: taskId
          in: query
          description: The unique task identifier returned when you created the task.
          required: true
          schema:
            type: string
            example: task_12345678
      responses:
        '200':
          description: Request successful
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        description: The task data object containing all task information
                        properties:
                          taskId:
                            type: string
                            description: The unique identifier for this task
                            example: task_12345678
                          model:
                            type: string
                            description: >-
                              The model used for this task (e.g.,
                              grok-imagine/text-to-image, seedream-4.0,
                              kling-1.0)
                            example: grok-imagine/text-to-image
                          state:
                            type: string
                            description: Current state of the task
                            enum:
                              - waiting
                              - queuing
                              - generating
                              - success
                              - fail
                            example: success
                          param:
                            type: string
                            description: >-
                              JSON string containing the original request
                              parameters used to create the task
                            example: >-
                              {"model":"grok-imagine/text-to-image","callBackUrl":"https://your-domain.com/api/callback","input":{"prompt":"Cinematic
                              portrait...","aspect_ratio":"3:2"}}
                          resultJson:
                            type: string
                            description: >-
                              JSON string containing the generated content URLs.
                              Only present when state is success. Structure
                              depends on outputMediaType: {resultUrls: []} for
                              image/media/video, {resultObject: {}} for text
                            example: >-
                              {"resultUrls":["https://example.com/generated-content.jpg"]}
                          failCode:
                            type: string
                            description: >-
                              Error code if the task failed. Empty string if
                              successful
                            example: ''
                          failMsg:
                            type: string
                            description: >-
                              Error message if the task failed. Empty string if
                              successful
                            example: ''
                          costTime:
                            type: integer
                            format: int64
                            description: >-
                              Processing time in milliseconds (available when
                              successful)
                            example: 15000
                          completeTime:
                            type: integer
                            format: int64
                            description: >-
                              Completion timestamp (Unix timestamp in
                              milliseconds)
                            example: 1698765432000
                          createTime:
                            type: integer
                            format: int64
                            description: >-
                              Creation timestamp (Unix timestamp in
                              milliseconds)
                            example: 1698765400000
                          updateTime:
                            type: integer
                            format: int64
                            description: Update timestamp (Unix timestamp in milliseconds)
                            example: 1698765432000
              example:
                code: 200
                msg: success
                data:
                  taskId: task_12345678
                  model: grok-imagine/text-to-image
                  state: success
                  param: >-
                    {"model":"grok-imagine/text-to-image","callBackUrl":"https://your-domain.com/api/callback","input":{"prompt":"Cinematic
                    portrait...","aspect_ratio":"3:2"}}
                  resultJson: '{"resultUrls":["https://example.com/generated-content.jpg"]}'
                  failCode: ''
                  failMsg: ''
                  costTime: 15000
                  completeTime: 1698765432000
                  createTime: 1698765400000
                  updateTime: 1698765432000
        '400':
          description: Bad Request - Missing or invalid taskId parameter
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ApiResponse'
              example:
                code: 400
                msg: taskId parameter is required
        '401':
          description: Unauthorized - Invalid or missing API key
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ApiResponse'
              example:
                code: 401
                msg: Unauthorized
        '404':
          description: Task Not Found - The specified taskId does not exist
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ApiResponse'
              example:
                code: 404
                msg: Task not found
        '429':
          description: Rate Limited - Too many requests
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ApiResponse'
              example:
                code: 429
                msg: Rate limit exceeded
        '500':
          $ref: '#/components/responses/Error'
components:
  schemas:
    ApiResponse:
      type: object
      properties:
        code:
          type: integer
          enum:
            - 200
            - 401
            - 402
            - 404
            - 422
            - 429
            - 455
            - 500
            - 501
            - 505
          description: >-
            Response status code


            - **200**: Success - Request has been processed successfully

            - **401**: Unauthorized - Authentication credentials are missing or
            invalid

            - **402**: Insufficient Credits - Account does not have enough
            credits to perform the operation

            - **404**: Not Found - The requested resource or endpoint does not
            exist

            - **422**: Validation Error - The request parameters failed
            validation checks

            - **429**: Rate Limited - Request limit has been exceeded for this
            resource

            - **455**: Service Unavailable - System is currently undergoing
            maintenance

            - **500**: Server Error - An unexpected error occurred while
            processing the request

            - **501**: Generation Failed - Content generation task failed

            - **505**: Feature Disabled - The requested feature is currently
            disabled
        msg:
          type: string
          description: Response message, error description when failed
          example: success
  responses:
    Error:
      description: Server Error
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: API Key
      description: >-
        All APIs require authentication via Bearer Token.


        Get API Key:

        1. Visit [API Key Management Page](https://kie.ai/api-key) to get your
        API Key


        Usage:

        Add to request header:

        Authorization: Bearer YOUR_API_KEY


        Note:

        - Keep your API Key secure and do not share it with others

        - If you suspect your API Key has been compromised, reset it immediately
        in the management page

````

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://docs.kie.ai/llms.txt

# Seedream4.5 - Edit

> Image editing by Seedream4.5

## Query Task Status

After submitting a task, use the unified query endpoint to check progress and retrieve results:

<Card title="Get Task Details" icon="magnifying-glass" href="/market/common/get-task-detail">
  Learn how to query task status and retrieve generation results
</Card>

<Tip>
  For production use, we recommend using the `callBackUrl` parameter to receive automatic notifications when generation completes, rather than polling the status endpoint.
</Tip>

## Related Resources

<CardGroup cols={2}>
  <Card title="Market Overview" icon="store" href="/market/quickstart">
    Explore all available models
  </Card>

  <Card title="Common API" icon="gear" href="/common-api/get-account-credits">
    Check credits and account usage
  </Card>
</CardGroup>


## OpenAPI

````yaml market/seedream/4.5-edit.json post /api/v1/jobs/createTask
openapi: 3.0.0
info:
  title: Seedream API
  description: kie.ai Seedream API Documentation
  version: 1.0.0
  contact:
    name: Technical Support
    email: support@kie.ai
servers:
  - url: https://api.kie.ai
    description: API Server
security:
  - BearerAuth: []
paths:
  /api/v1/jobs/createTask:
    post:
      summary: Generate content using seedream/4.5-edit
      operationId: seedream-4-5-edit
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - model
              properties:
                model:
                  type: string
                  enum:
                    - seedream/4.5-edit
                  default: seedream/4.5-edit
                  description: |-
                    The model name to use for generation. Required field.

                    - Must be `seedream/4.5-edit` for this endpoint
                  example: seedream/4.5-edit
                callBackUrl:
                  type: string
                  format: uri
                  description: >-
                    The URL to receive generation task completion updates.
                    Optional but recommended for production use.


                    - System will POST task status and results to this URL when
                    generation completes

                    - Callback includes generated content URLs and task
                    information

                    - Your callback endpoint should accept POST requests with
                    JSON payload containing results

                    - Alternatively, use the Get Task Details endpoint to poll
                    task status
                  example: https://your-domain.com/api/callback
                input:
                  type: object
                  description: Input parameters for the generation task
                  properties:
                    prompt:
                      description: >-
                        A text description of the image you want to generate
                        (Max length: 3000 characters)
                      type: string
                      maxLength: 3000
                      example: >-
                        Keep the model's pose and the flowing shape of the
                        liquid dress unchanged. Change the clothing material
                        from silver metal to completely transparent clear water
                        (or glass). Through the liquid water, the model's skin
                        details are visible. Lighting changes from reflection to
                        refraction.
                    image_urls:
                      description: >-
                        Upload an image file to use as input for the API (File
                        URL after upload, not file content; Accepted types:
                        image/jpeg, image/png, image/webp; Max size: 10.0MB)
                      type: array
                      items:
                        type: string
                        format: uri
                      maxItems: 14
                      example:
                        - >-
                          https://static.aiquickdraw.com/tools/example/1764851484363_ScV1s2aq.webp
                    aspect_ratio:
                      description: >-
                        Width-height ratio of the image, determining its visual
                        form.
                      type: string
                      enum:
                        - '1:1'
                        - '4:3'
                        - '3:4'
                        - '16:9'
                        - '9:16'
                        - '2:3'
                        - '3:2'
                        - '21:9'
                      default: '1:1'
                      example: '1:1'
                    quality:
                      description: Basic outputs 2K images, while High outputs 4K images.
                      type: string
                      enum:
                        - basic
                        - high
                      default: basic
                      example: basic
                  required:
                    - prompt
                    - image_urls
                    - aspect_ratio
                    - quality
            example:
              model: seedream/4.5-edit
              callBackUrl: https://your-domain.com/api/callback
              input:
                prompt: >-
                  Keep the model's pose and the flowing shape of the liquid
                  dress unchanged. Change the clothing material from silver
                  metal to completely transparent clear water (or glass).
                  Through the liquid water, the model's skin details are
                  visible. Lighting changes from reflection to refraction.
                image_urls:
                  - >-
                    https://static.aiquickdraw.com/tools/example/1764851484363_ScV1s2aq.webp
                aspect_ratio: '1:1'
                quality: basic
      responses:
        '200':
          description: Request successful
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          taskId:
                            type: string
                            description: >-
                              Task ID, can be used with Get Task Details
                              endpoint to query task status
                            example: task_seedream_1765172101886
              example:
                code: 200
                msg: success
                data:
                  taskId: task_seedream_1765172101886
        '500':
          $ref: '#/components/responses/Error'
components:
  schemas:
    ApiResponse:
      type: object
      properties:
        code:
          type: integer
          enum:
            - 200
            - 401
            - 402
            - 404
            - 422
            - 429
            - 455
            - 500
            - 501
            - 505
          description: >-
            Response status code


            - **200**: Success - Request has been processed successfully

            - **401**: Unauthorized - Authentication credentials are missing or
            invalid

            - **402**: Insufficient Credits - Account does not have enough
            credits to perform the operation

            - **404**: Not Found - The requested resource or endpoint does not
            exist

            - **422**: Validation Error - The request parameters failed
            validation checks

            - **429**: Rate Limited - Request limit has been exceeded for this
            resource

            - **455**: Service Unavailable - System is currently undergoing
            maintenance

            - **500**: Server Error - An unexpected error occurred while
            processing the request

            - **501**: Generation Failed - Content generation task failed

            - **505**: Feature Disabled - The requested feature is currently
            disabled
        msg:
          type: string
          description: Response message, error description when failed
          example: success
  responses:
    Error:
      description: Server Error
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: API Key
      description: >-
        All APIs require authentication via Bearer Token.


        Get API Key:

        1. Visit [API Key Management Page](https://kie.ai/api-key) to get your
        API Key


        Usage:

        Add to request header:

        Authorization: Bearer YOUR_API_KEY


        Note:

        - Keep your API Key secure and do not share it with others

        - If you suspect your API Key has been compromised, reset it immediately
        in the management page

````

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://docs.kie.ai/llms.txt