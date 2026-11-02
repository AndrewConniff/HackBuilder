using System.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace Brokerage.Web.Pages;

[ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
[IgnoreAntiforgeryToken]
/// <summary>Shows an error reference without disclosing exception details.</summary>
public class ErrorModel : PageModel
{
    /// <summary>Gets or sets the request correlation identifier.</summary>
    public string? RequestId { get; set; }

    /// <summary>Indicates whether a correlation identifier is available.</summary>
    public bool ShowRequestId => !string.IsNullOrEmpty(RequestId);

    /// <summary>Loads the current trace reference.</summary>
    public void OnGet()
    {
        RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier;
    }

    /// <summary>Shows failures raised by form submissions.</summary>
    public void OnPost() => OnGet();
}
