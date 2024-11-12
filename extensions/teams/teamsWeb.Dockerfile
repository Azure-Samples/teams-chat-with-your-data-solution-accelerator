FROM node:18.18.0 as development
ENV PORT=80
EXPOSE 80
WORKDIR /usr/app

ENV NODE_ENV=development
COPY ["package*.json", "./"]
RUN npm install && mv node_modules ../
COPY . .
RUN chown -R node /usr/app
USER node
CMD ["npm", "run", "dev"]

FROM development as build
RUN npm run build

FROM node:18.18.0-alpine as production
ENV PORT=80
EXPOSE 80
WORKDIR /usr/app

ENV NODE_ENV=production
COPY --from=build /usr/app/lib ./lib
COPY --from=build /usr/node_modules ./node_modules
CMD ["node", "lib/index.js"]
