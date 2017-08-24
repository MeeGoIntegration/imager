$(document).ready(function() {

  $("select[name=template]").change(function() {
     var selected = $(this).val();
     console.log(selected);
     var selected_elem = $("option[value$='" + selected + "']");
     console.log(selected_elem);
     $($(selected_elem)[0].attributes).each( function() {
       var x = this;
       console.log(x.name);
       if (x.name.match(/^data-/)) {
         var y = x.name.replace("data-", "");
         console.log(y);
         if (x.value.match(/,/)) {
           console.log('aaaaaaaaa');
           $(x.value.split(",")).each( function() {
             $("[name=" + y + "][value=" + this + "]").attr("checked", true);
           });
         } else {
           $("[name=" + y + "]").val(x.value);
         }
       }
     });
  });
});
