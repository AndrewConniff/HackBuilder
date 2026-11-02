FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY NuGet.Config .
COPY src/Restaurant.Web/Restaurant.Web.csproj src/Restaurant.Web/
COPY src/Restaurant.Web/packages.lock.json src/Restaurant.Web/
RUN dotnet restore src/Restaurant.Web/Restaurant.Web.csproj --configfile /src/NuGet.Config --locked-mode
COPY src/Restaurant.Web/ src/Restaurant.Web/
RUN dotnet publish src/Restaurant.Web/Restaurant.Web.csproj -c Release -o /app/publish --no-restore /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
USER $APP_UID
ENTRYPOINT ["dotnet", "Restaurant.Web.dll"]
