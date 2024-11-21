# GitHub Actions Workflows

This document provides an overview of the GitHub Actions workflows used in this project.

## Workflows

### 1. Reusable Docker Build and Push Workflow

**File:** `.github/workflows/reusable-build-push-docker-image.yml`

This workflow builds and pushes Docker images to Azure Container Registry (ACR).

**Inputs:**
- `dockerfile`: (Required) The path to the Dockerfile.
- `image_name`: (Required) The name of the Docker image.
- `tag_name`: (Required) The tag of the Docker image.

**Jobs:**
- `docker-build-push`: This job performs the following steps:
  - **Checkout Code**: Checks out the code from the repository.
  - **Evaluate environment value**: Determines the environment (DEV or PROD) based on the branch on which workflow is being run.
  - **Get ACR details**: Generates the Azure Container Registry details and stores them as environment variables.
  - **Docker Login**: Logs in to the Azure Container Registry.
  - **Set up Docker Buildx**: Sets up Docker Buildx for building multi-platform images.
  - **Set Docker tags**: Sets the Docker image tags.
  - **Build Docker Image and push**: Builds the Docker image using the specified Dockerfile and pushes it to the ACR.

### 2. Reusable Docker Image Deploy Workflow

**File:** `.github/workflows/reusable-deploy-docker-image.yml`

This workflow is used to deploy Docker images to Azure App Services or Azure Function Apps.

**Inputs:**
- `service_name`: (Optional) The name of the service to deploy.
- `deploy_command`: (Required) The deployment command (`app-service` or `function-app`).
- `image_name`: (Required) The name of the Docker image.
- `tag_name`: (Required) The tag of the Docker image.

**Jobs:**
- `deploy`: This job performs the following steps:
  - **Evaluate environment value**: Determines the environment (DEV or PROD) based on the branch on which workflow is being run.
  - **Get ACR name and other details**: Retrieves the Azure Container Registry and other details from the environment variables.
  - **Set service name**: Sets the service name based on the input `service_name`.
  - **Azure Login**: Logs in to Azure using the managed identity.
  - **Set Image name**: Sets the Docker image name.
  - **Set Azure App Service container settings**: Configures the Azure App Service to use the specified Docker image (if `deploy_command` is `app-service`).
  - **Set Azure Function App container settings**: Configures the Azure Function App to use the specified Docker image (if `deploy_command` is `function-app`).

### 3. Reusable Docker Copy Image Workflow

**File:** `.github/workflows/reusable-copy-docker-image.yml`

This workflow copies Docker images from one ACR to another.

**Inputs:**
- `image_name`: (Required) The name of the Docker image.
- `source_environment`: (Required) The source environment (e.g., `dev`).
- `destination_environment`: (Required) The destination environment (e.g., `prod`).

### 4. Teams App - Build and Deploy Docker Image

**File:** `.github/workflows/build-deploy-docker-images-teams-app.yml`

This workflow builds and deploys the Teams App Docker image.

**Triggers:**
- `workflow_dispatch`
- `push` to `main` branch for `extensions/teams/**` path
- `pull_request` to `main` branch for `extensions/teams/**` path

**Jobs:**
- `build-push-docker-image`: Builds the Docker image for the Teams App and pushes it to the Azure Container Registry (ACR).
- `deploy-app`: Deploys the Docker image to the Azure App Service.
- `copy-acr-image`: Copies the Docker image from the development ACR to the production ACR when changes are pushed to the `main` branch.

### 5. Frontend App - Build and Deploy Docker Image

**File:** `.github/workflows/build-deploy-docker-images-frontend.yml`

This workflow builds and deploys the Frontend App Docker image.

**Triggers:**
- `workflow_dispatch`
- `push` to `main` branch for `code/frontend/src/**` path
- `pull_request` to `main` branch for `code/frontend/src/**` path

**Jobs:**
- `build-push-docker-image`: Builds the Docker image for the Frontend App and pushes it to the ACR.
- `deploy-app`: Deploys the Docker image to the Azure App Service.
- `copy-acr-image`: Copies the Docker image from the development ACR to the production ACR when changes are pushed to the `main` branch.

### 6. Backend App - Build and Deploy Docker Image

**File:** `.github/workflows/build-deploy-docker-images-backend.yml`

This workflow builds and deploys the Backend App Docker image.

**Triggers:**
- `workflow_dispatch`
- `push` to `main` branch for `code/backend/batch/**` path
- `pull_request` to `main` branch for `code/backend/batch/**` path

**Jobs:**
- `build-push-docker-image`: Builds the Docker image for the Backend App and pushes it to the ACR.
- `deploy-app`: Deploys the Docker image to the Azure Function App.
- `copy-acr-image`: Copies the Docker image from the development ACR to the production ACR when changes are pushed to the `main` branch.

### 7. Admin - Frontend App - Build and Deploy Docker Image

**File:** `.github/workflows/build-deploy-docker-images-admin-frontend.yml`

This workflow builds and deploys the Admin Frontend App Docker image.

**Triggers:**
- `workflow_dispatch`
- `push` to `main` branch for `code/backend/Admin.py` and `code/backend/pages/**` paths
- `pull_request` to `main` branch for `code/backend/Admin.py` and `code/backend/pages/**` paths

**Jobs:**
- `build-push-docker-image`: Builds the Docker image for the Admin Frontend App and pushes it to the ACR.
- `deploy-app`: Deploys the Docker image to the Azure App Service.
- `copy-acr-image`: Copies the Docker image from the development ACR to the production ACR when changes are pushed to the `main` branch.

## How to Run the Workflows

### Running Workflows Manually

You can manually trigger any of the workflows using the `workflow_dispatch` event. To do this:

1. Go to the "Actions" tab in your GitHub repository.
2. Select the workflow you want to run.
3. Click on the "Run workflow" button.
4. Fill in any required inputs and click "Run workflow".

### Running Workflows on Push or Pull Request

The workflows are also triggered automatically on specific events:

- **Push to Main Branch:** When code is pushed to the `main` branch in the specified paths, the workflows will run automatically.
- **Pull Request to Main Branch:** When a pull request is opened, ready for review, reopened, or synchronized to the `main` branch in the specified paths, the workflows will run automatically.

### Example: Running the Teams App Workflow

To run the Teams App workflow manually:

1. Go to the "Actions" tab in your GitHub repository.
2. Select the "Teams App - Build and Deploy Docker Image" workflow.
3. Click on the "Run workflow" button.
4. Fill in the required inputs and click "Run workflow".

To trigger the workflow automatically, push changes to the `extensions/teams/**` path or create a pull request with changes in that path to the `main` branch.

### Secrets used in the workflows

The workflows use the following secrets:

![GitHub Actions Workflows Secrets](./images/github_Actions_workflows_secrets.png)

| Secret Name                          | Description                                      | Example Value                  |
|--------------------------------------|--------------------------------------------------|--------------------------------|
| `DEV_AZURE_CONTAINER_REGISTRY`       | Azure Container Registry for development         | `devacr.azurecr.io`            |
| `DEV_AZURE_CONTAINER_REGISTRY_USER_NAME` | Username for development ACR                    | `devacrusername`               |
| `DEV_AZURE_CONTAINER_REGISTRY_PASSWORD` | Password for development ACR                    | `devacrpassword`               |
| `DEV_AZURE_RESOURCE_GROUP`           | Resource group for development                   | `dev-resource-group`           |
| `DEV_AZURE_BACKEND_FUNCTION_APP_NAME`| Backend function app name for development        | `dev-backend-function-app`     |
| `DEV_AZURE_FRONTEND_APP_NAME`        | Frontend app name for development                | `dev-frontend-app`             |
| `DEV_AZURE_ADMIN_APP_SERVICE_NAME`   | Admin app service name for development           | `dev-admin-app-service`        |
| `DEV_TEAMS_APP_NAME`                 | Teams app name for development                   | `dev-teams-app`                |
| `DEV_AZURE_CLIENT_ID`                | Azure client ID for development                  | `<CLIENT_ID_OF_MANAGED_IDENTITY>`                |
| `DEV_AZURE_TENANT_ID`                | Azure tenant ID for development                  | `<TENANT_ID_DEV_ENV>`                |
| `DEV_AZURE_SUBSCRIPTION_ID`          | Azure subscription ID for development            | `<SUBSCRIPTION_ID_DEV_ENV>`          |


> **Note:** Depending on how the release process is designed and how many environments are involved, please revisit the list of secrets required for a production-ready environment.

## Further references:

### Azure Login Step Using Managed Identity

The Azure Login step in the workflows uses a managed identity to authenticate with Azure. This step requires the following values:

- `client-id`: The client ID of the User Assigned Managed Identity.
- `tenant-id`: The tenant ID of the Azure subscription.
- `subscription-id`: The subscription ID of the Azure subscription.

These values are provided as secrets in the GitHub repository. To use a managed identity for authentication, you need to set up federated credentials in Azure. Federated credentials allow GitHub Actions to authenticate using the managed identity without needing to store credentials directly in the repository.

#### Setting Up Federated Credentials

1. **Create a User Assigned Managed Identity**: You can create a User Assigned Managed Identity using the Azure portal, Azure CLI, or a Bicep template.

2. **Configure Federated Credentials**: Configure federated credentials for the managed identity to allow GitHub Actions to authenticate. This involves specifying the issuer, subject, and audience for the federated credential.

3. **Assign Roles**: Assign the necessary roles to the managed identity to allow it to perform actions in your Azure subscription.

For more details on setting up federated credentials, refer to the following documentation:

- [Configure federated credentials for a managed identity](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust-user-assigned-managed-identity?pivots=identity-wif-mi-methods-azp)
- [Azure Login GitHub Action](https://github.com/Azure/login)

### Create a User Assigned Managed Identity with Federated Credentials



Below is a code sample using Bicep to deploy a User Assigned Managed Identity and configure a federated credential for GitHub Actions. This Bicep template can be deployed at the Resource Group level.

```bicep
/*
This Bicep template deploys a User Assigned Managed Identity and configures a federated credential for GitHub Actions.

Parameters:
- servicePrincipalName (string): The name of the User Assigned Managed Identity.
- environment (string): The environment name (e.g., 'dev', 'prod') to be used in the federated credential. This example uses environment value, however, there are other settings as well to be used in the subject, like branch name, tag name, pull request. Please review the GitHub documentation for more details and choose the appropriate value for your setup.
- githubRepo (string): The GitHub repository in the format 'owner/repo'.
- location (string, optional): The Azure region where the resources will be deployed. Default is 'uksouth'.

Resources:
- spApp: Deploys a User Assigned Managed Identity.
- sp: Assigns the Contributor role to the User Assigned Managed Identity.
- federatedCredential: Configures a federated credential for GitHub Actions to authenticate using the User Assigned Managed Identity.

Outputs:
- clientId (string): The client ID of the User Assigned Managed Identity.
- tenantId (string): The tenant ID of the Azure subscription.
*/
param servicePrincipalName string
param environment string
param githubRepo string
param location string = 'uksouth'

resource spApp 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: servicePrincipalName
  location: location
}

resource sp 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(subscription().id, resourceGroup().id, servicePrincipalName)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Contributor role ID
    principalId: spApp.properties.principalId
  }
}

resource federatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-07-31-preview' = {
  parent: spApp
  name: 'GitHubFederatedCredential-${environment}'
  properties: {

    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepo}:environment:${environment}'
    audiences: [
      'api://AzureADTokenExchange'
    ]
  }
}

output clientId string = spApp.properties.clientId
output tenantId string = subscription().tenantId

```

### Deploying the Bicep Template

To deploy the Bicep template at the resource group level, you can use the following Azure CLI command:
```
   az deployment group create \
          --resource-group <resource_group_name> \
          --template-file <path_to_bicep_template> \
          --parameters servicePrincipalName=<name_of_user_assigned_managed_identity>  environment=<environment_value_to_set_in_subject>  githubRepo=<gh_repo_name>
```


**Disclaimer:** This code is provided as-is and is not meant for use on a production environment.The end user must test and modify the code to suit their target environment. Ensure thorough testing and necessary adjustments before using it in production.
