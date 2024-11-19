const config = {
  botId: process.env.BOT_ID,
  botPassword: process.env.BOT_PASSWORD,
  azureFunctionUrl: process.env.AZURE_FUNCTION_URL,
  cosmosEndpoint: process.env.COSMOSDB_ENDPOINT,
  cosmosPassword: process.env.COSMOSDB_KEY,
  cosmosDatabaseName: process.env.COSMOSDB_DATABASE_NAME,
  cosmosContainerName: process.env.COSMOSDB_CONTAINER_NAME
};

export default config;
