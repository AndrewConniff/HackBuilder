FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source
COPY src/Brokerage.Web/Brokerage.Web.csproj src/Brokerage.Web/
RUN dotnet restore src/Brokerage.Web/Brokerage.Web.csproj
COPY src/Brokerage.Web/ src/Brokerage.Web/
COPY data/ data/
RUN dotnet publish src/Brokerage.Web/Brokerage.Web.csproj -c Release -o /app /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app .
ENV ASPNETCORE_HTTP_PORTS=8080
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "Brokerage.Web.dll"]
