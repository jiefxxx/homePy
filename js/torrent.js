var SERVER="127.0.0.1:8080"

var app = angular.module('Torrent', []);

app.controller('myCtrl',function($scope,$interval,$http){
    $scope.propertyName = 'position';
    $scope.reverse = true;

    $scope.getFiles = function(){
        $("#torrent").trigger('click');
        console.log("test");
    };

    $scope.sortBy = function(propertyName) {
        $scope.reverse = ($scope.propertyName === propertyName) ? !$scope.reverse : false;
        $scope.propertyName = propertyName;
     };

    $scope.convert_bytes = function(value){
        if (value == 0){
            return "0 B"
        }
        var size_name = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
        var pre = Math.log(value)/Math.log(1024)
        var i = Math.floor(pre)
        var p = Math.pow(1024, i)
        var s = (value/p).toFixed(2)
        return s+" "+size_name[i]
    }

    $scope.uploadFile = function(files) {
        var fd = new FormData();
        //Take the first selected file
        fd.append("file", files[0]);
        $.ajax({
            url: 'http://'+SERVER+'/torrent.html',
            type: 'post',
            data: fd,
            processData: false,
            contentType: false,
            success: function (data) {
                console.log("ok")
            }
        });

    };

    $scope.refresh_torrent = function(){
        $.ajax({
            url: 'http://'+SERVER+'/torrent/info',
            type: 'get',
            dataType: 'json',
            success: function (data) {
                $scope.names = data;
            }
        });
    };
    $scope.add = function (){
        $.ajax({
            url: 'http://'+SERVER+'/tm/add',
            type: 'post',
            dataType: 'json',
            success: function (data) {
                console.log(data);
                $scope.url = "";
            },
            data: '{"torrent":"'+$scope.url+'"}'
        });
    };
    $scope.action = function(action, hash=null){
         var str_hash = "";
         if(hash != null){
            str_hash = "?hash="+hash
         }
         $.ajax({
            url: 'http://'+SERVER+'/torrent/'+action+str_hash,
            type: 'get',
            dataType: 'text',
            success: function (data) {
                console.log(action, data)
            }
        });
    };
    $scope.get_class = function(state){
        if(state=='downloading'){
            return 'success'
        }
        else if(state == 'seeding'){
            return 'warning'
        }
        else{
            return ""
        }
    };
    $scope.refresh_torrent();
    $interval(function () { $scope.refresh_torrent(); }, 1000);
});
