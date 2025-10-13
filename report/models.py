from django.db import models

class User(models.Model):
    name = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'users' 
        managed = False  
        
    def __str__(self):
        return self.name

