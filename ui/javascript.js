/*
 * CRM
 */

var initial_company;
var widget_name;

// Hide the company Edition/Creation form
function crm_hide_company_form()
{
    $('#company').hide();
    $('select[name=' + widget_name  +']').val(initial_company);
}

// Add a link which hide the Edit/New company form
function crm_add_close_link()
{
    // Add a link to hide the company Edition/Creation form
    $('fieldset#company legend').append('\
        <a id="hide-company-form" onclick="crm_hide_company_form();">X</a>');
}

function crm_show_company_form()
{
    crm_add_close_link();
    $('#company').show();
}

function crm_show_edit()
{
    selected_company = $('select[name=' + widget_name +']').val();
    if (selected_company != initial_company)
        if (selected_company != '')
            return false;
    alert('The changes will apply to all contacts of this company');
    $('fieldset#company legend').text('Edit company');
    crm_show_company_form();
    // Action on the company is an edit
    $('#action_on_company').val('edit')
}

function crm_show_new()
{
    $('fieldset#company legend').text('New company');
    // As the user decided to affect a new company to a contact, the value of
    // the selector widget is re-initialized.
    $('select[name=' + widget_name  +']').val('');
    crm_show_company_form();
    // Action on the company is a creation
    $('#action_on_company').val('new')
}

function company_scenario()
{
    // Did it really changed ?
    selected_company = $('select[name=' + widget_name + ']').val();
    // Yes so the company edition is disabled
    if (selected_company != initial_company){
        $("#edit-company").addClass("disabled");
        $("#edit-company").attr("title",
        "You can't edit the company because the selected company has changed");
    // No so the company edition is no more disabled
    }else{
        $("#edit-company").removeClass("disabled");
        $("#edit-company").removeAttr("title");
    }
    // The action on the company is not an update nor a new resource
    $('#action_on_company').val('');
}

function crm_main(select_widget, first_widget_id)
{
    // Get the initial affected company to the contact
    initial_company = $('select[name=' + select_widget + ']').val();
    // Get the crm_p_company selector name
    widget_name = select_widget;

    // Focus on the first_widget
    $('#' + first_widget_id).focus();
    // Hide the company Edition/Creation form
    $('#company').hide();
    // If the company affected to the contact has changed
    $('#company_widget').change(
        function()
        {
            company_scenario()
        });
}


/*
$(document).ready(function() {
    $("textarea").each(function() {
        var textarea = $(this);
        textarea.attr("_rows", textarea.attr("rows"));
        textarea.attr("rows", 1);
    });
    $("textarea").focus(function() {
        var textarea = $(this);
        textarea.attr("rows", textarea.attr("_rows"));
    });
    $("textarea").blur(function() {
        var textarea = $(this);
        textarea.attr("rows", 1);
    });
});
*/
