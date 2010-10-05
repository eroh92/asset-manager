(function(){
    /* comments should be stripped */
    var helloVariable = 'hello';
    var sayHello = function(removed){
        /* in the middle */
        alert(helloVariable);
    };
    sayHello(); // these should be too
})();