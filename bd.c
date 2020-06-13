                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   #include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>

int compare(time_t, time_t, time_t);
void Bday();
main(){
	Bday();
	while(true){
		time_t currentTime = time(NULL);
		struct tm* time = localtime(&currentTime);
		if(time->tm_hour == 0 &time->tm_min == 0&time->tm_sec == 5){
			Bday();
			sleep(1);
		}
	}
}
int compare(time_t y, time_t n, time_t current){
	if(difftime(y, current)>difftime(n, current)){
		return 1;
	}
	else if(difftime(y, current)==difftime(n,current)){
		return 0;
	}
	else{
		return -1;
	}
}

void Bday(){
	int i;
	time_t currentTime = time(NULL);
	char ch = '&';
	int count=0;
	int counter =0;
	FILE *fp = fopen("Data.txt", "r");
	if(fp == NULL){
		printf("Cannot find file");
	}
	while((ch = fgetc(fp)) != EOF){
		while(ch != '\n'&&ch != EOF){
			ch = (char)fgetc(fp);
		}
		counter++;
		if(counter==8){
			count++;
			counter =0;
		}
	}
	fclose(fp);
	int isName = 1;
	char* id[count];
	char* names[count];
	int age[count];
	struct tm prepare[count];
	time_t bday[count];
	int byear[count];
	FILE* f = fopen("Data.txt", "r");
	int counte = 0;
	while(counte < count){
		ch = fgetc(f);
		char* h = (char*)malloc(1000);
		h[0] = '\0';
		char* cha = (char*)malloc(sizeof(&ch));
		while(ch != '\n'&&ch != EOF){
			cha = &ch;
			*(cha+1) = *("");
			strcat(h, cha);
			ch = fgetc(f);
		}
		if(isName==1){
			ch = fgetc(f);
			names[counte] = h;
			while(ch != '\n'&&ch != EOF){
				ch = fgetc(f);
			}
			isName = 0;
		}
		else if(isName == 0){
			ch = fgetc(f);
			char* day = (char*)malloc(sizeof(h));
			day = h + 8;
			char* year= (char*)malloc(sizeof(h));
			for( i = 0; i< 4; i++){
				*(year+i) =*(h);
				h++;
			}
			h++;
			char*month =(char*)malloc(sizeof(h));
			for( i = 0; i< 2; i++){
				*(month+i) = *(h);
				h++;
			}
			sscanf(day, "%d", &prepare[counte].tm_mday);
			sscanf(month, "%d", &prepare[counte].tm_mon);
			sscanf(year, "%d", &byear[counte]);
			struct tm* now = localtime(&currentTime);
			prepare[counte].tm_year =  now->tm_year;
			prepare[counte].tm_mon = prepare[counte].tm_mon - 1;
			prepare[counte].tm_sec = 59;
			prepare[counte].tm_min = 59;
			prepare[counte].tm_hour = 23;
			for(i =0; i< 4;i++){
				while(ch != '\n'&&ch != EOF){
					ch = fgetc(f);
				}
				if(i==3){
					break;
				}
				ch = fgetc(f);
			}
			isName = 2;
		}
		else{
			id[counte] = h;
			isName = 1;
			counte++;
		}
	}
	fclose(f);
	for(i = 0; i< count;i++){
		bday[i] = mktime(&prepare[i]);
		struct tm* temp = localtime(&bday[i]);
		if(temp->tm_hour ==0){
			temp->tm_hour = 23;
			temp->tm_mday = temp -> tm_mday -1;
		}
		else{
			temp->tm_hour = 23;
		}
		bday[i] = mktime(temp);
		age[i] =prepare->tm_year-  (byear[i]- 1900) ;
	}
	for(i = 0; i<count; i++){
		if(difftime(bday[i], currentTime)<0){
			struct tm* temp = localtime(&bday[i]);
			if(temp->tm_hour ==0){
				temp->tm_hour = 23;
				temp->tm_mday = temp -> tm_mday -1;
			}
			else{
				temp->tm_hour = 23;
			}
			temp->tm_year = temp->tm_year+1;
			bday[i] = mktime(temp);
			age[i] = age[i] + 1;
		}
	}
	char* string = "";
	int t= 0;
	time_t temp = NULL;
	int te = 0;
	for(int i  = 0; i< count-1; i++){
		t = i;
		for(int j = i+1;j<count;j++){
			if(compare(bday[j], bday[t], currentTime) <=0){
				t = j;
			}
		}
		string = names[i];
		names[i] = names[t];
		names[t] = string;
		string = id[i];
		id[i] = id[t];
		id[t] = string;
		temp = bday[i];
		bday[i] = bday[t];
		bday[t] = temp;
		te = age[i];
		age[i] = age[t];
		age[t] = te;
	}
	FILE* file = fopen("scan.txt", "w");
	for(int i = 0; i< count; i++){
		if((age[i]<=20)&&(age[i] >= 13)||(strcmp("greg neat", names[i]) == 0)){
			struct tm* temp = localtime(&bday[i]);
			if(temp->tm_hour ==0){
				temp->tm_mday = temp -> tm_mday -1;
			}
			fprintf(file, "%s*%d!%d@%d#%d^%s,", names[i],temp->tm_mon,temp->tm_mday,temp->tm_year+1900,age[i],id[i]);
		}
	}
	fclose(file);
}
