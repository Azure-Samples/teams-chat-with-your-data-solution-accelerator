import {
  TeamsActivityHandler,
  TurnContext,
  CardFactory,
  ActivityTypes,
  MessageFactory
} from "botbuilder";
import config from "./config";
import {
  ChatMessage,
  ChatResponse,
  ToolMessageContent,
  Citation,
} from "./model";
import { cwydResponseBuilder } from "./cards/cardBuilder";

const EMPTY_RESPONSE = "Sorry, I do not have an answer. Please try again.";

const history: ChatMessage[] = []; // JM+ Store the user's message in the history

// Function to clear history after a period of time
const clearHistory = () => {
  history.length = 0;
};

// Set an interval to clear history every 2 minutes (120000 milliseconds)
//setInterval(clearHistory, 120000);

export class TeamsBot extends TeamsActivityHandler {
  constructor() {
    super();
    let newActivity;
    let assistantAnswer = "";
    let answerwithdisclaimertext = "";
    let activityUpdated = true;


    this.onMessage(async (context, next) => {
      console.log("Running with Message Activity.");

      //JM added the clear history functionality
      const activity = context.activity;
      if (activity.value && activity.value.action === "clearHistory") {
        // Clear the chat history
        history.length = 0;
        await context.sendActivity("Chat history has been cleared.");
        return;
      }
      const removedMentionText = TurnContext.removeRecipientMention(
        context.activity
      );
      const txt = removedMentionText.toLowerCase().replace(/\n|\r/g, "").trim();
      try {
        const reply = await context.sendActivity("Searching ...");

        const typingReply = await context.sendActivities([
          { type: ActivityTypes.Typing },
        ]);

        // Create a new activity with the user's message as a reply.
        const answers: ChatMessage[] = [];
        const userMessage: ChatMessage = {
          role: "user",
          content: txt,
        };
        history.push(userMessage); // JM+ Store the user's message in the history
        const httpBody = JSON.stringify({
          messages: history, //JM amended to include the user's message
          conversation_id: "",
        });
        console.log(httpBody);
        // Call the Azure Function to get the response from Azure OpenAI on your Data
        let result = {} as ChatResponse;
        try {

          const response = await fetch(config.azureFunctionUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: httpBody,
          });

          // Parse the response
          if (response?.body) {
            const reader = response.body.getReader();
            let runningText = "";
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              var text = new TextDecoder("utf-8").decode(value);
              console.log(text);
              const objects = text.split("\n");
              objects.forEach((obj) => {
                try {
                  runningText += obj;
                  result = JSON.parse(runningText);
                  if (result.error) {
                    answers.push(userMessage, {
                      role: "error",
                      content:
                        "ERROR: " + result.error + " | " + EMPTY_RESPONSE,
                    });
                  } else {
                    answers.push(userMessage, ...result.choices[0].messages);
                    history.push(result.choices[0].messages[result.choices[0].messages.length - 1]); // JM+ Store the assistant's last message in the history
                  }
                  runningText = "";
                } catch (e) {
                  const errorMessage: ChatMessage = {
                    role: "error",
                    content: e.message,
                  };
                  answers.push(errorMessage);
                }
              });
            }
          }
        } catch (e) {
          console.error(e);
          const errorMessage: ChatMessage = {
            role: "error",
            content: e.message,
          };
          answers.push(errorMessage);
        }

        // Parse the citations from the tool message
        const parseCitationFromMessage = (message: ChatMessage) => {
          if (message.role === "tool") {
            try {
              const toolMessage = JSON.parse(
                message.content
              ) as ToolMessageContent;
              return toolMessage.citations;
            } catch {
              return [];
            }
          }
          return [];
        };

        // Generate the response for the user
        answers.map((answer, index) => {
          if (answer.role === "assistant") {
            assistantAnswer = answer.content;
            answerwithdisclaimertext = assistantAnswer + "<div style='color:#707070;font-size:12px;font-family: Segoe UI;font-style: normal;font-weight: 400; line-height: 16px; margin-top: 15px; padding-bottom: 5px;'>AI-generated content may be incorrect</div>" ;
            if (assistantAnswer.startsWith("[doc")) {
              assistantAnswer = EMPTY_RESPONSE;
              newActivity = MessageFactory.text(answerwithdisclaimertext);
            } else {
              const citations = parseCitationFromMessage(answers[index - 1]) as Citation[];
              //JM need to look at how we can add the clear history button here
              if (citations.length === 0) {
                newActivity = MessageFactory.text(answerwithdisclaimertext);
                newActivity.id = reply.id;
              } else {
                newActivity = MessageFactory.attachment(cwydResponseBuilder(citations, assistantAnswer));
                activityUpdated = false;
              }
            }
  

          } else if (answer.role === "error") {
            newActivity = MessageFactory.text(
              "Sorry, an error occurred. Try waiting a few minutes. If the issue persists, contact your system administrator. Error: " +
              answer.content
            );
            newActivity.id = reply.id;
          }

        });
        newActivity.typing = false; // Stop the ellipses visual indicator

        if (activityUpdated) {
          await context.updateActivity(newActivity);
        } else {
            try {
              await context.deleteActivity(reply.id);
            } catch (error) {
              console.log('Error in deleting message', error);
            }
            await context.sendActivity(newActivity);
        }
        

      } catch (error) {
        console.log('Error in onMessage:', error);
      } finally {
      }

      // By calling next() you ensure that the next BotHandler is run.
      await next();
    });

    this.onMembersAdded(async (context, next) => {
      const membersAdded = context.activity.membersAdded;
      for (let cnt = 0; cnt < membersAdded.length; cnt++) {
        if (membersAdded[cnt].id) {
          await context.sendActivity(
            `Greetings! I am the Chat with your data bot. How can I help you today?`
          );
          break;
        }
      }
      await next();
    });

    }
}
