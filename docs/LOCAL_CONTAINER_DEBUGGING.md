[Back to *Chat with your data* README](../README.md)

# Local docker setup

The easiest way to run this accelerator is in a VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

Assuming all these steps have been done in the [local setup](./LOCAL_DEPLOYMENT.md)

## Build all of the images

From the root of the project:

```
docker build -f docker/Admin.Dockerfile -t local-admin:1 .
docker build -f docker/Frontend.Dockerfile -t local-web:1 .
docker build -f docker/Backend.Dockerfile -t local-func:1 .
```
choose your own names for the docker images.

## Push these images to an Azure Container Registry

Firstly, make sure a container registry (ACR) has been created and if you are using keys, enable "admin" for the ACR instance.

Login to the ACR

```
az login --tenant f69a7636-4db8-498c-8ff6-bc7f1aafcec0
az acr login --name jjtestacr

```
now tag and push images

```
docker tag local-web:1 jjtestacr.azurecr.io/teams-accel-web:1
docker push jjtestacr.azurecr.io/teams-accel-web:1
docker tag local-func:1  jjtestacr.azurecr.io/teams-accel-func:1
docker push jjtestacr.azurecr.io/teams-accel-func:1
docker tag local-admin:1  jjtestacr.azurecr.io/teams-accel-admin:1
docker push jjtestacr.azurecr.io/teams-accel-admin:1
```

Using your own ACR name and your choice of image names.

## Debug the containers locally

It is often useful to debug the containers locally. This requires:
1. make sure that there is a .env file with the correct values for each container or one common superset of values
2. for the functions container, a secret will need to be injected. More on this later.

### Local Admin container run

```
docker run -it --env-file ./.env-admin  -p 8080:80 local-admin:1
```

### Local web container run

```
docker run -it --env-file ./.env-web  -p 8081:80 local-web:1
```

### Local functions container run

```
docker run -it --env-file ./.env.oldfunc  -p 8082:80 -v ${HOST_DOCKER_FOLDER:-.}/keys:/azure-functions-host/Secrets local-func:1
```

in the above, we are taking the file ./docker/function-host.json and copying it to /.docker/keys/hosts.json and then using the "-v" option to mount this file into the container in /azure-functions-hosts/secrets as the file *hosts.json*.

A .gitignore file has been added to the repo to exclude the local hosts.json file from being pushed to the repository

#### Alternative method using a dedicated docker volume

A docker volume can also be used to manage the hosts file so it is external to the repository. The only issue with this is locating the actual folder for the volume within the docker infrastructure of the host file system. Typically on Windows running WSL, this is likely to be
`\\WSL$\docker-desktop-data\version-pack-data\community\docker\volumes`

Choose a name for the volume and create it :

```
docker volume create teams-app-keys
```

As above, copy ./docker/function-host.json into this volume and call it *hosts.json*

Amend the docker run command :

```
docker run -it --env-file ./.env.oldfunc  -p 8080:80 -v teams-app-keys:/azure-functions-host/Secrets local-func:1
```

This will allow a REST request to be sent to the running docker container in the following form:

```
### call the function that wraps the API
POST http://0.0.0.0:8080/api/GetConversationResponse?code=some-test-key
Content-Type: application/json

{
    "conversation_id": "1234",
    "messages": [
        {
            "role": "user",
            "content": "What key components are needed to produce a successful creative marketing strategy?"
        }
    ]
}
```

As can be seen from the above, the functions URL is */api/GetConversationResponse* and it is authenticated using *code-some-test-key* where the value is in hosts.json. You can amend this file for a different secret.
