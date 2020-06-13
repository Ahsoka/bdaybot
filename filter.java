import java.util.*;
import java.io.*;
import java.awt.*;
import java.awt.image.BufferedImage;
class filter{
    public static void main(String[] args){
        filter f = new filter();
        f.filt();
        Timer timer = new Timer();
        TimerTask tt = new TimerTask(){
            public void run(){
                Calendar cal = Calendar.getInstance(); 
				int hour = cal.get(Calendar.HOUR_OF_DAY);
                int minute = cal.get(Calendar.MINUTE);
                int second = cal.get(Calendar.SECOND);
				if(hour == 0&&minute == 0&&second ==10){
                    f.filt();
				}
            }
        };
        timer.schedule(tt, 1000, 1000);   
    }
    public void filt(){
        BufferedWriter w = null;
        BufferedReader r = null;
        try{
            File tex= new File("read.txt");
            FileWriter wr = new FileWriter(tex);
            w = new BufferedWriter(wr);
            File text = new File("scan.txt");
            Scanner reader = new Scanner(text);
            ArrayList<String> texts = new ArrayList<String>();
            r= new BufferedReader(new FileReader(new File("Student Locator Spring 2020.csv")));
            String f = "";
            while(reader.hasNext()){
                f = f + reader.nextLine();
            }
            String[] split = f.split(",");
            String line = null;
            for(int i = 0; i< split.length; i++){
                while ((line = r.readLine())!=null){
                    String[] splitrow = line.split(",");
                    String name =   splitrow[2] + " "+splitrow[1];
                    name = name.toLowerCase();
                    String t = split[i].toLowerCase();
                    if(t.contains(name)||(t.contains("greg neat"))){
                        w.write(split[i]+",");
                        break;
                    }
                }
                r.close();
                r= new BufferedReader(new FileReader(new File("Student Locator Spring 2020.csv")));
            }
        }
        catch(Exception e){
            e.printStackTrace();
        }
        finally{
            if((w != null)&&(r!=null)){
                try{
                    w.close();
                    r.close();
                }
                catch(Exception e){
                    e.printStackTrace();
                 }
            }
        }
    }
}
