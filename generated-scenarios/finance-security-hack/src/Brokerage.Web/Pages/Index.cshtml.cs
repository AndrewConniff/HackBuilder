using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Brokerage.Web.Pages;

/// <summary>The anonymous gateway's customer education landing page.</summary>
public sealed class IndexModel : PageModel
{
    /// <summary>Renders the chat shell without reading customer or application data.</summary>
    public void OnGet() { }
}
