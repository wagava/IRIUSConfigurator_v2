
$("#btn_upload").on('click', function (e){
    e.preventDefault();
    let btn = $(this);
    btn.attr("disabled", true);
  
    $.ajax({
  
        url: "{% url 'variables:upload_variables' object.n_controller.id %}?min={{object.id}}&max={{object.id}}&action=upload",     
  
        type: "GET",
  
        success: function (data) {
            btn.attr("disabled", false);
            if (data) {
                console.log(data);
                console.log('выполнился success');
                if (data.return_block.length > 0)
                {
                var messages = ['Данные в БД и ПЛК не соответствуют по следующим позициям:\r\n\r\n'];
  
                console.log(data.return_block)
                //alert(data.error_back);                    
                for (var x=0; x<data.return_block.length; x++)
                {
                    console.log(data.return_block[x])
                    messages.push(data.return_block[x] + '\r\n\r\n')
                }
                alert(messages);
                }
                else
                {alert('Данные в БД и ПЛК идентичны');}
  
                
            }
            
        }
      });
});

 