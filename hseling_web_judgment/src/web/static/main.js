
function getUrlVars()
{
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
    }
    return vars;
}

$(function () {
  var vars = getUrlVars(),
      task_id = vars["task_id"];

  if(task_id) {
    var get_status = function () {
      $.get("status?task_id=" + task_id, function(data) {
        if (data.ready) {
          $(".lead").text(data.result);
          $(".raw").text(atob(data.raw_base64));
        } else {
          setTimeout(get_status, 2000);
        }
      });
    };

    get_status();
  }
});

