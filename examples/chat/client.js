var socket = require('engine.io-client')('http://localhost:5000'),
    http = require('http');

socket.on('open', function(){
    console.log('opened');

    socket.write('hello');

    socket.on('message', function(message){
        console.log('on_message ' + message)
    });
    socket.on('close', function(){
        console.log('close');
    });
});

socket.on('error', function (exception) {
    console.log(exception);
});


http.createServer(function (req, res) {
    res.writeHead(200, {'Content-Type': 'text/plain'});
    res.end('INDEX');
}).listen(9615);
