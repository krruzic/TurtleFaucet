document.addEventListener('DOMContentLoaded', function () {
  new Fingerprint2().get(function(result, components){
    $('input[name="fingerprint"]').val(result); //a hash, representing your device fingerprint
  });
  $('.notification-center').hide();
  // Get all "navbar-burger" elements
  var $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
  // Check if there are any navbar burgers
  if ($navbarBurgers.length > 0) {
    // Add a click event on each of them
    $navbarBurgers.forEach(function ($el) {
      $el.addEventListener('click', function () {
        // Get the target from the "data-target" attribute
        var target = $el.dataset.target;
        var $target = document.getElementById(target);
        // Toggle the class on both the "navbar-burger" and the "navbar-menu"
        $el.classList.toggle('is-active');
        $target.classList.toggle('is-active');
      });
    });
  }
});


$("#addressinput").attr('placeholder',"TRTLv3YFzEtDMrpWXAFgLRiB4Cfk7Gs1yUM2Z6wYzGZi6up1HHHNTpx5XysQJVJL2fJC7qx6RWkCXWmygFsaNYHUFMFN5rJMmM5");

if (parseInt($("#numshells").text())<=100) {
  $("#addressinput").prop('disabled',true);
  $("#addressinput").attr('placeholder',"The Faucet is too low! Come back later");
} else {
  $("#addressinput").prop('disabled',false);
  $("#addressinput").attr('placeholder',"TRTLv3YFzEtDMrpWXAFgLRiB4Cfk7Gs1yUM2Z6wYzGZi6up1HHHNTpx5XysQJVJL2fJC7qx6RWkCXWmygFsaNYHUFMFN5rJMmM5");
}

$('#getshells').click(function() {
  $.ajax({
    url: '/pour',
    data: $('#shellform').serialize(),
    type: 'POST',
    beforeSend: function(xhr, settings) {
      $('.notification-center').show();
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrf_token);
      }
    },
    success: function(response) {
      $('#successmessage').fadeIn(1000);
      $('#successmessage').fadeOut(3000);
      grecaptcha.reset();
      $('.notification-center').fadeout(3000);
    },
    error: function(error) {
      $('#errormessage').fadeIn(1000);
      $('#err_message').text(JSON.parse(error.responseText).reason);
      $('#errormessage').fadeOut(3000);
      grecaptcha.reset();
      $('.notification-center').fadeOut(3000);
    }
  });
});

$('#successmessage').click(function() {
  $('#successmessage').hide();
});
$('#errormessage').click(function() {
  $('#errormessage').hide();
});
