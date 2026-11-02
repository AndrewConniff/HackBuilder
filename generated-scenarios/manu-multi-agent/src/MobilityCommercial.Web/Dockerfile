FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY NuGet.Config .
COPY src/MobilityCommercial.Web/MobilityCommercial.Web.csproj src/MobilityCommercial.Web/
COPY src/MobilityCommercial.Web/packages.lock.json src/MobilityCommercial.Web/
RUN dotnet restore src/MobilityCommercial.Web/MobilityCommercial.Web.csproj --configfile NuGet.Config --locked-mode
COPY src/MobilityCommercial.Web/ src/MobilityCommercial.Web/
RUN dotnet publish src/MobilityCommercial.Web/MobilityCommercial.Web.csproj -c Release --no-restore -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_HTTP_PORTS=8080
ENV DOTNET_EnableDiagnostics=0
EXPOSE 8080
USER $APP_UID
ENTRYPOINT ["dotnet", "MobilityCommercial.Web.dll"]
