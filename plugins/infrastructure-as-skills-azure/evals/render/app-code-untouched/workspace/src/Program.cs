// appdemo - a status page that shows which Key Vault the app is configured for.
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// APP-SENTINEL-UNCHANGED: the app's owner decides this name, not the infrastructure render.
var vaultEndpoint = builder.Configuration["KEYVAULT_ENDPOINT"];

app.MapGet("/", () => vaultEndpoint is null ? "vault: not configured" : "vault: configured");
app.Run();
